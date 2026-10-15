import logging
import os
from pathlib import Path
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from datetime import datetime
from typing import Any
from urllib.parse import parse_qs
import winreg

import pystray
from PIL import Image
from windows_toasts import (
    InteractableWindowsToaster,
    Toast,
    ToastButton,
    ToastInputTextBox,
    ToastProgressBar,
    WindowsToaster,
)

from Database import DataBase
from Settings import Settings
from config import BASE_DIR, METADATA
from i18n import text


logger = logging.getLogger(__name__)
_AUTO_START_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
_AUTO_START_NAME = METADATA["name"]


def _auto_start_command(script_path: str | Path | None = None) -> str:
    if getattr(sys, "frozen", False) or "__compiled__" in globals():
        command = [str(Path(sys.argv[0]).resolve())]
    else:
        entrypoint = Path(script_path) if script_path is not None else Path("main.py")
        if not entrypoint.is_absolute():
            entrypoint = BASE_DIR / entrypoint
        command = [sys.executable, str(entrypoint.resolve())]
    return subprocess.list2cmdline(command)


def _auto_start_on(command: str | None = None) -> None:
    if os.name != "nt":
        raise OSError("Automatic startup is only supported on Windows.")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, _AUTO_START_KEY) as key:
        winreg.SetValueEx(
            key,
            _AUTO_START_NAME,
            0,
            winreg.REG_SZ,
            command or _auto_start_command(),
        )


def _auto_start_of() -> None:
    if os.name != "nt":
        raise OSError("Automatic startup is only supported on Windows.")
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _AUTO_START_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, _AUTO_START_NAME)
    except FileNotFoundError:
        return


class TrayIcon:
    def __init__(
        self,
        show: Callable[[], None],
        hide: Callable[[], None],
        on_exit: Callable[[], None],
        img: Image.Image | None = None,
    ) -> None:
        self._show_callback = show
        self._hide_callback = hide
        self._exit_callback = on_exit
        self._stopped = False
        self.tray = pystray.Icon(
            f"{METADATA['name']}-{METADATA['version']}",
            img if img is not None else self.generate_img(),
            f"{METADATA['name']} Tray Icon",
        )
        self.tray.title = f"{METADATA['name']}-{METADATA['version']}"
        self.tray.menu = pystray.Menu(
            pystray.MenuItem("Show", self._show),
            pystray.MenuItem("Hide", self._hide),
            pystray.MenuItem("Exit", self._exit),
        )

    @staticmethod
    def generate_img() -> Image.Image:
        return Image.new("RGB", (64, 64), color=(0, 150, 255))

    def _show(self, _icon: Any, _item: Any) -> None:
        self._show_callback()

    def _hide(self, _icon: Any, _item: Any) -> None:
        self._hide_callback()

    def _exit(self, _icon: Any, _item: Any) -> None:
        self._exit_callback()
        self.stop()

    def run(self) -> None:
        self.tray.run()

    def run_detached(self) -> None:
        self.tray.run_detached()

    def stop(self) -> None:
        if not self._stopped:
            self.tray.stop()
            self._stopped = True


def Notify_Task(
    task_name: str,
    details: list[str],
    on_activated: Callable[[], None] | None = None,
) -> None:
    toaster = WindowsToaster(f"{METADATA['name']}-{METADATA['version']}")
    toast = Toast(text_fields=[task_name, *details])
    if on_activated is not None:
        toast.on_activated = lambda _args: on_activated()
    toaster.show_toast(toast)


def Notificate_Task(
    task_name: str,
    details: list[str],
    progress: float | None = None,
    on_action: Callable[[str, str | None], None] | None = None,
    language: str = "Vie",
) -> None:
    toaster = InteractableWindowsToaster(
        f"{METADATA['name']}-{METADATA['version']}"
    )

    def dispatch(activated_args: Any) -> None:
        if on_action is None:
            return
        arguments = parse_qs(str(activated_args.arguments or ""))
        action = arguments.get("action", ["launch"])[0]
        inputs = activated_args.inputs or {}
        note = inputs.get("change_note")
        on_action(action, str(note) if note is not None else None)

    toast = Toast(
        text_fields=[task_name, *details],
        progress_bar=(
            ToastProgressBar(
                caption=text("toast_progress", language),
                status=text("toast_in_progress", language),
                progress=progress,
            )
            if progress is not None
            else None
        ),
    )
    toast.inputs.append(
        ToastInputTextBox(
            input_id="change_note",
            placeholder=text("toast_note_placeholder", language),
            caption=text("toast_note_caption", language),
        )
    )
    toast.actions.extend(
        [
            ToastButton(
                content=text("toast_change", language),
                arguments="action=submit",
            ),
            ToastButton(
                content=text("toast_launch", language),
                arguments="action=launch",
            ),
            ToastButton(
                content=text("toast_change_launch", language),
                arguments="action=change_and_launch",
            ),
            ToastButton(
                content=text("toast_done", language),
                arguments="action=task_done",
            ),
        ]
    )

    toast.on_activated = dispatch
    toaster.show_toast(toast)


class BackgroundRuntime:
    CHECK_INTERVAL_SECONDS = 5

    def __init__(
        self,
        database: DataBase,
        settings: Settings,
        show_callback: Callable[[], None] | None = None,
        hide_callback: Callable[[], None] | None = None,
        open_task_callback: Callable[[str], None] | None = None,
        tasks_changed_callback: Callable[[], None] | None = None,
    ) -> None:
        self.database = database
        self.settings = settings
        self.stop_event = threading.Event()
        self.show_callback = show_callback or self._show_console_message
        self.hide_callback = hide_callback or settings.hide_console
        self.open_task_callback = open_task_callback or (
            lambda _name: self.show_callback()
        )
        self.tasks_changed_callback = tasks_changed_callback or (lambda: None)
        self.tray: TrayIcon | None = None
        self._thread: threading.Thread | None = None
        self._deadline_alerts_sent: dict[str, str] = {}

    @staticmethod
    def _show_console_message() -> None:
        print("TasksHere is running in this console. Use CLI commands here.")

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return

        if os.name == "nt":
            self.tray = TrayIcon(
                self.show_callback,
                self.hide_callback,
                self.stop_event.set,
            )
            try:
                self.tray.run_detached()
            except Exception:
                logger.exception("Could not start the system tray icon")
                print("Warning: the system tray icon could not be started.")
                self.tray = None

        self._thread = threading.Thread(
            target=self._run,
            name="taskshere-background",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self.stop_event.set()
        if self.tray is not None:
            self.tray.stop()
        if self._thread is not None and self._thread is not threading.current_thread():
            self._thread.join(timeout=2)
            if self._thread.is_alive():
                logger.warning("Background worker did not stop within two seconds")
                print("Warning: the background worker is still stopping.")

    def _run_safely(self, action_name: str, action: Callable[[], None]) -> None:
        try:
            action()
        except Exception:
            logger.exception("Background action failed: %s", action_name)
            print(f"Warning: background action failed: {action_name}. Check the log.")

    def _refresh_weights(self) -> None:
        self.database.refresh_weights()
        self.tasks_changed_callback()

    def _run(self) -> None:
        self._run_safely("startup weight refresh", self._refresh_weights)
        self._run_safely("startup task reminder", self._notify_top_task)
        self._run_safely("deadline alerts", self._check_deadline_alerts)

        last_reminder = time.monotonic()
        last_weight_refresh = last_reminder
        while not self.stop_event.wait(self.CHECK_INTERVAL_SECONDS):
            now = time.monotonic()
            reminder_minutes = int(self.settings.RemindTask)
            if reminder_minutes and now - last_reminder >= reminder_minutes * 60:
                self._run_safely("periodic task reminder", self._notify_top_task)
                last_reminder = now

            refresh_minutes = int(self.settings.AutoRefestWeight)
            if (
                refresh_minutes
                and now - last_weight_refresh >= refresh_minutes * 60
            ):
                self._run_safely(
                    "periodic weight refresh", self._refresh_weights
                )
                last_weight_refresh = now

            if self.settings.TimeAlertBeforeDeadline:
                self._run_safely("deadline alerts", self._check_deadline_alerts)

    def _notify_top_task(self) -> None:
        tasks = [
            task
            for task in self.database.get_tasks()
            if not self.database.is_timed_out(task)
        ]
        if not tasks:
            return
        task = tasks[0]
        name = DataBase._task_name(task)
        info = task.get("info", [])
        language = str(self.settings.Language)
        details = [
            text("toast_deadline", language, deadline=info[10]),
            text("toast_priority", language, weight=task.get("weight", 0)),
        ]
        note = task.get("note")
        if note:
            details.append(text("toast_note", language, note=note))
        self._send_task_notification(
            name,
            text("toast_reminder_title", language, name=name),
            details,
        )

    def _send_task_notification(
        self, task_name: str, title: str, details: list[str]
    ) -> None:
        if getattr(self.settings, "Toast detail") == "Detailed":
            Notificate_Task(
                title,
                details,
                on_action=lambda action, note: self._handle_toast_action(
                    task_name, action, note
                ),
                language=str(self.settings.Language),
            )
        else:
            Notify_Task(
                title,
                details,
                on_activated=lambda: self.open_task_callback(task_name),
            )

    def _handle_toast_action(
        self, task_name: str, action: str, note: str | None
    ) -> None:
        try:
            if action in {"submit", "change_and_launch"} and note is not None:
                task = self.database.get_task(task_name)
                if task is None:
                    logger.warning(
                        "Ignoring toast action for missing task %r", task_name
                    )
                    return
                self.database.update_task(
                    task_name,
                    task["info"],
                    note,
                )
                self.tasks_changed_callback()
            if action in {"launch", "change_and_launch"}:
                self.open_task_callback(task_name)
            elif action == "task_done":
                self.database.remove_task(task_name)
                self.tasks_changed_callback()
                logger.info("Task %r marked done from toast", task_name)
            elif action not in {"submit", "change_and_launch", "launch"}:
                logger.warning("Ignoring unknown toast action %r", action)
        except (OSError, ValueError, KeyError, TypeError):
            logger.exception(
                "Could not process toast action %r for task %r",
                action,
                task_name,
            )

    def _check_deadline_alerts(self) -> None:
        alert_minutes = int(self.settings.TimeAlertBeforeDeadline)
        if not alert_minutes:
            return

        current_time = datetime.now()
        current_task_alerts: dict[str, str] = {}
        for task in self.database.get_tasks():
            name = DataBase._task_name(task)
            info = task.get("info")
            if not isinstance(info, list) or len(info) <= 10:
                logger.warning("Skipping deadline alert for task %r with invalid info", name)
                continue
            deadline_text = info[10]
            if not isinstance(deadline_text, str):
                logger.warning("Skipping deadline alert for task %r with invalid deadline", name)
                continue
            try:
                deadline = datetime.strptime(deadline_text, DataBase.DATE_FORMAT)
            except ValueError:
                logger.warning(
                    "Skipping deadline alert for task %r with invalid deadline %r",
                    name,
                    deadline_text,
                )
                continue

            alert_key = name.casefold()
            current_task_alerts[alert_key] = deadline_text
            seconds_remaining = (deadline - current_time).total_seconds()
            if (
                0 <= seconds_remaining <= alert_minutes * 60
                and self._deadline_alerts_sent.get(alert_key) != deadline_text
            ):
                rounded_minutes = max(1, int((seconds_remaining + 59) // 60))
                language = str(self.settings.Language)
                self._send_task_notification(
                    name,
                    text("toast_deadline_title", language, name=name),
                    [
                        text(
                            "toast_due_in",
                            language,
                            minutes=rounded_minutes,
                        ),
                        text("toast_deadline", language, deadline=deadline_text),
                    ],
                )
                self._deadline_alerts_sent[alert_key] = deadline_text

        self._deadline_alerts_sent = {
            name: deadline
            for name, deadline in self._deadline_alerts_sent.items()
            if current_task_alerts.get(name) == deadline
        }
