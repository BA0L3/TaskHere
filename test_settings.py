import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from Settings import Settings


class SettingsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "settings.json"

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_missing_file_defaults_auto_start_to_false(self) -> None:
        settings = Settings(self.path)

        self.assertFalse(settings.auto_start)
        self.assertFalse(getattr(settings, "Just Show Only TrayIon"))

    def test_show_only_tray_setting_is_persisted(self) -> None:
        settings = Settings(self.path)
        settings.set_values(**{"Just Show Only TrayIon": True})

        self.assertTrue(
            getattr(Settings(self.path), "Just Show Only TrayIon")
        )

    def test_auto_start_setting_is_persisted(self) -> None:
        settings = Settings(self.path)
        settings.set_auto_start(True)

        self.assertTrue(Settings(self.path).auto_start)
        self.assertEqual(
            json.loads(self.path.read_text(encoding="utf-8")),
            {**Settings.DEFAULTS, "auto_start": True},
        )

    def test_new_settings_are_validated_and_persisted(self) -> None:
        settings = Settings(self.path)
        settings.set_values(
            TimeAlertBeforeDeadline=15,
            AutoPrintList=True,
            RemindTask=30,
            AutoRefestWeight=60,
        )

        loaded = Settings(self.path)
        self.assertEqual(loaded.TimeAlertBeforeDeadline, 15)
        self.assertTrue(loaded.AutoPrintList)
        self.assertEqual(loaded.RemindTask, 30)
        self.assertEqual(loaded.AutoRefestWeight, 60)

    def test_appearance_language_and_toast_settings_are_persisted(self) -> None:
        settings = Settings(self.path)
        settings.set_values(mode="Dark", Language="Eng", **{"Toast detail": "Detailed"})

        loaded = Settings(self.path)
        self.assertEqual(loaded.mode, "Dark")
        self.assertEqual(loaded.Language, "Eng")
        self.assertEqual(getattr(loaded, "Toast detail"), "Detailed")

    def test_invalid_appearance_language_and_toast_values_are_rejected(self) -> None:
        settings = Settings(self.path)

        with self.assertRaisesRegex(ValueError, "mode"):
            settings.set_values(mode="Blue")
        with self.assertRaisesRegex(ValueError, "Language"):
            settings.set_values(Language="French")
        with self.assertRaisesRegex(ValueError, "Toast detail"):
            settings.set_values(**{"Toast detail": "Verbose"})

    def test_negative_interval_is_rejected(self) -> None:
        settings = Settings(self.path)

        with self.assertRaisesRegex(ValueError, "non-negative"):
            settings.set_values(RemindTask=-1)

        self.assertEqual(settings.RemindTask, 0)

    def test_invalid_json_is_regenerated_with_auto_start_enabled(self) -> None:
        self.path.write_text("{invalid", encoding="utf-8")

        settings = Settings(self.path)

        self.assertTrue(settings.auto_start)
        self.assertIsNotNone(settings.recovery_message)
        self.assertEqual(
            json.loads(self.path.read_text(encoding="utf-8")),
            {
                **Settings.DEFAULTS,
                "auto_start": True,
            },
        )

    def test_non_boolean_auto_start_is_regenerated(self) -> None:
        self.path.write_text('{"auto_start": "yes"}', encoding="utf-8")

        settings = Settings(self.path)

        self.assertTrue(settings.auto_start)
        self.assertEqual(
            json.loads(self.path.read_text(encoding="utf-8")),
            {
                **Settings.DEFAULTS,
                "auto_start": True,
            },
        )

    def test_non_object_settings_are_regenerated(self) -> None:
        self.path.write_text("[]", encoding="utf-8")

        settings = Settings(self.path)

        self.assertTrue(settings.auto_start)
        self.assertEqual(
            json.loads(self.path.read_text(encoding="utf-8")),
            {
                **Settings.DEFAULTS,
                "auto_start": True,
            },
        )

    def test_undecodable_settings_are_regenerated(self) -> None:
        self.path.write_bytes(b"\xff")

        settings = Settings(self.path)

        self.assertTrue(settings.auto_start)
        self.assertEqual(
            json.loads(self.path.read_text(encoding="utf-8")),
            {
                **Settings.DEFAULTS,
                "auto_start": True,
            },
        )

    def test_disable_console_close_disables_the_system_close_command(self) -> None:
        settings = Settings(self.path)
        kernel32 = Mock()
        user32 = Mock()
        kernel32.GetConsoleWindow.return_value = 123
        user32.GetSystemMenu.return_value = 456
        user32.EnableMenuItem.return_value = 0
        user32.DrawMenuBar.return_value = True

        def load_library(name: str, **kwargs: object) -> Mock:
            self.assertTrue(kwargs["use_last_error"])
            return {"kernel32": kernel32, "user32": user32}[name]

        with (
            patch("Settings.os.name", "nt"),
            patch("Settings.ctypes.WinDLL", side_effect=load_library),
        ):
            self.assertTrue(settings.disable_console_close())

        user32.EnableMenuItem.assert_called_once_with(456, 0xF060, 0x0001)
        user32.DrawMenuBar.assert_called_once_with(123)

    def test_hide_and_show_console_update_visibility(self) -> None:
        settings = Settings(self.path)
        settings.hwnd = 123
        user32 = Mock()

        with (
            patch("Settings.os.name", "nt"),
            patch("Settings.ctypes.WinDLL", return_value=user32),
        ):
            settings.hide_console()
            self.assertFalse(settings.console_visible)
            settings.show_console()

        self.assertTrue(settings.console_visible)
        self.assertEqual(
            [call.args[1] for call in user32.ShowWindow.call_args_list],
            [0, 5],
        )
        user32.SetForegroundWindow.assert_called_once_with(123)


if __name__ == "__main__":
    unittest.main()
