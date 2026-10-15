import json
import os
import tempfile
from pathlib import Path
import ctypes
from ctypes import wintypes

from config import SETTINGS_FILE


class Settings:
    DEFAULTS: dict[str, bool | int | str] = {
        "auto_start": False,
        "TimeAlertBeforeDeadline": 12*60,
        "AutoPrintList": False,
        "RemindTask": 0,
        "AutoRefestWeight": 60,
        "mode": "Light",
        "Language": "Vie",
        "Toast detail": "Simple",
        "Just Show Only TrayIon": False,
    }
    OPTIONS: dict[str, tuple[str, ...]] = {
        "mode": ("Light", "Dark"),
        "Language": ("Vie", "Eng"),
        "Toast detail": ("Simple", "Detailed"),
    }

    def __init__(self, path: str | os.PathLike[str] = SETTINGS_FILE) -> None:
        self.path = Path(path)
        self.recovery_message: str | None = None
        self._values = self._load_values()
        self.hwnd: int | None = None
        self.console_visible = True

    def _load_values(self) -> dict[str, bool | int | str]:
        try:
            with self.path.open("r", encoding="utf-8") as file:
                values = json.load(file)
        except FileNotFoundError:
            self._values = dict(self.DEFAULTS)
            self.save()
            return dict(self._values)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return self._recover(f"the file could not be decoded ({exc})")

        if not isinstance(values, dict):
            return self._recover("the file must contain a JSON object")

        loaded_values = dict(self.DEFAULTS)
        for name, default in self.DEFAULTS.items():
            value = values.get(name, default)
            if type(default) is bool:
                if not isinstance(value, bool):
                    return self._recover(f"{name} must be a boolean")
            elif isinstance(default, str):
                if not isinstance(value, str) or value not in self.OPTIONS[name]:
                    return self._recover(
                        f"{name} must be one of {', '.join(self.OPTIONS[name])}"
                    )
            elif not isinstance(value, int) or isinstance(value, bool) or value < 0:
                return self._recover(f"{name} must be a non-negative integer")
            loaded_values[name] = value
        if any(name not in values for name in self.DEFAULTS):
            self._values = loaded_values
            self.save()
        return loaded_values

    def _recover(self, reason: str) -> dict[str, bool | int | str]:
        self._values = dict(self.DEFAULTS)
        self._values["auto_start"] = True
        self.save()
        self.recovery_message = (
            f"Settings were invalid ({reason}); settings.json was regenerated "
            "with safe default values and auto_start enabled."
        )
        return dict(self._values)

    def __getattr__(self, name: str) -> bool | int | str:
        if name in self.DEFAULTS and "_values" in self.__dict__:
            return self._values[name]
        raise AttributeError(f"{type(self).__name__!s} has no setting {name!r}")

    def set_auto_start(self, enabled: bool) -> None:
        self.set_values(auto_start=enabled)

    def set_values(self, **updates: bool | int | str) -> None:
        for name, value in updates.items():
            if name not in self.DEFAULTS:
                raise KeyError(f"Unknown setting: {name}")
            default = self.DEFAULTS[name]
            if type(default) is bool:
                if not isinstance(value, bool):
                    raise TypeError(f"The {name} setting must be a boolean.")
            elif isinstance(default, str):
                if not isinstance(value, str) or value not in self.OPTIONS[name]:
                    raise ValueError(
                        f"The {name} setting must be one of "
                        f"{', '.join(self.OPTIONS[name])}."
                    )
            elif not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError(
                    f"The {name} setting must be a non-negative integer."
                )

        previous_values = self._values.copy()
        self._values.update(updates)
        try:
            self.save()
        except OSError:
            self._values = previous_values
            raise

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as file:
                temporary_path = file.name
                json.dump(self._values, file, indent=4)
                file.write("\n")
            os.replace(temporary_path, self.path)
        except OSError:
            if temporary_path and os.path.exists(temporary_path):
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass
            raise

    def _get_console_window(self) -> int | None:
        if os.name != "nt":
            raise OSError("Console window controls are only supported on Windows.")
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_console_window = kernel32.GetConsoleWindow
        get_console_window.restype = wintypes.HWND
        self.hwnd = get_console_window()
        return self.hwnd

    def disable_console_close(self) -> bool:
        hwnd = self._get_console_window()
        if hwnd is None:
            return False

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        get_system_menu = user32.GetSystemMenu
        get_system_menu.argtypes = (wintypes.HWND, wintypes.BOOL)
        get_system_menu.restype = wintypes.HMENU
        system_menu = get_system_menu(hwnd, False)
        if not system_menu:
            return False

        enable_menu_item = user32.EnableMenuItem
        enable_menu_item.argtypes = (wintypes.HMENU, wintypes.UINT, wintypes.UINT)
        enable_menu_item.restype = wintypes.UINT
        ctypes.set_last_error(0)
        result = enable_menu_item(system_menu, 0xF060, 0x0001)
        if result == 0xFFFFFFFF:
            error_code = ctypes.get_last_error()
            if error_code:
                raise ctypes.WinError(error_code)
            raise OSError("Could not disable the console close command.")

        draw_menu_bar = user32.DrawMenuBar
        draw_menu_bar.argtypes = (wintypes.HWND,)
        draw_menu_bar.restype = wintypes.BOOL
        if not draw_menu_bar(hwnd):
            error_code = ctypes.get_last_error()
            if error_code:
                raise ctypes.WinError(error_code)
            raise OSError("Could not refresh the console window menu.")
        return True

    def hide_console(self) -> None:
        hwnd = self.hwnd or self._get_console_window()
        if hwnd is None:
            raise OSError("No console window is available to hide.")
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        show_window = user32.ShowWindow
        show_window.argtypes = (wintypes.HWND, ctypes.c_int)
        show_window.restype = wintypes.BOOL
        show_window(hwnd, 0)
        self.console_visible = False

    def show_console(self) -> None:
        hwnd = self.hwnd or self._get_console_window()
        if hwnd is None:
            raise OSError("No console window is available to show.")
        user32 = ctypes.WinDLL("user32", use_last_error=True)
        show_window = user32.ShowWindow
        show_window.argtypes = (wintypes.HWND, ctypes.c_int)
        show_window.restype = wintypes.BOOL
        show_window(hwnd, 5)
        set_foreground_window = user32.SetForegroundWindow
        set_foreground_window.argtypes = (wintypes.HWND,)
        set_foreground_window.restype = wintypes.BOOL
        set_foreground_window(hwnd)
        self.console_visible = True

    def toggle_console(self) -> None:
        if self.console_visible:
            self.hide_console()
        else:
            self.show_console()
