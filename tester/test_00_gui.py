import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QMessageBox

from Database import DataBase
from Settings import Settings
from config import WEIGHTS
from gui import MainWindow, SettingsDialog, TaskDialog
from main_gui import _should_start_hidden


class GuiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.application = QApplication.instance() or QApplication([])

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.database = DataBase(root / "tasks.json")
        self.settings = Settings(root / "settings.json")
        future = datetime.now() + timedelta(days=1)
        self.database.new_task(
            [3.0] * 10 + [future.strftime(DataBase.DATE_FORMAT)],
            "Active task",
            "Some notes",
        )
        past_info = [2.0] * 10 + [
            (datetime.now() - timedelta(minutes=5)).strftime(
                DataBase.DATE_FORMAT
            )
        ]
        timed_out = {
            "task_name": "Expired task",
            "info": past_info,
            "note": "Past deadline",
            "created_at": datetime.now().strftime(DataBase.DATE_FORMAT),
            "weight": 0,
        }
        self.database._write_tasks(
            [*self.database.get_tasks(), timed_out]
        )

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_refresh_separates_active_and_timed_out_tasks(self) -> None:
        window = MainWindow(self.database, WEIGHTS, self.settings)

        self.assertEqual(window.task_table.rowCount(), 1)
        self.assertEqual(window.timeout_table.rowCount(), 1)
        expired_name = window.timeout_table.item(0, 0)
        if expired_name is None:
            self.fail("The timed-out task name was not shown")
        self.assertEqual(expired_name.text(), "Expired task")

        window.refresh_timer.stop()
        window.close()

    def test_clear_button_removes_all_expired_tasks_only(self) -> None:
        window = MainWindow(self.database, WEIGHTS, self.settings)
        window.refresh_timer.stop()
        with patch(
            "gui.QMessageBox.question",
            return_value=QMessageBox.StandardButton.Yes,
        ):
            window._clear_timed_out_tasks()

        self.assertIsNone(self.database.get_task("Expired task"))
        self.assertIsNotNone(self.database.get_task("Active task"))
        self.assertEqual(window.timeout_table.rowCount(), 0)
        window.close()

    def test_language_and_dark_mode_are_applied(self) -> None:
        window = MainWindow(self.database, WEIGHTS, self.settings)
        window.refresh_timer.stop()
        self.settings.set_values(mode="Dark", Language="Eng")
        window._apply_theme()
        window._apply_language()

        self.assertEqual(window.active_title.text(), "Active tasks")
        self.assertEqual(window.clear_button.text(), "Clear all")
        self.assertIn("#171a21", window.styleSheet())
        self.assertIn("#372e2e", window.styleSheet())
        window.close()

    def test_deadline_calendar_has_explicit_light_and_weekend_colors(self) -> None:
        dialog = TaskDialog(WEIGHTS, language="Eng", mode="Light")

        calendar_stylesheet = dialog.deadline_input.calendarWidget().styleSheet()
        self.assertIn("#E2E2E2", calendar_stylesheet)
        self.assertIn("background-color: #E2E2E2", calendar_stylesheet)
        self.assertEqual(
            dialog.deadline_input.calendarWidget().weekdayTextFormat(
                Qt.DayOfWeek.Saturday
            ).foreground().color().name(),
            "#d64545",
        )

    def test_dropdowns_use_palette_colors(self) -> None:
        window = MainWindow(self.database, WEIGHTS, self.settings)
        window.refresh_timer.stop()

        self.assertIn("QComboBox::drop-down", window.styleSheet())
        self.assertIn("QComboBox QAbstractItemView", window.styleSheet())
        self.assertIn("#e3e3e3", window.styleSheet())
        window.close()

    def test_show_only_tray_setting_is_available_in_settings_dialog(self) -> None:
        dialog = SettingsDialog(self.settings)
        control = dialog.controls["Just Show Only TrayIon"]
        self.assertIsInstance(control, QCheckBox)
        control.setChecked(True)
        dialog._save()
        self.assertTrue(getattr(self.settings, "Just Show Only TrayIon"))

    def test_startup_hides_window_only_when_tray_is_available(self) -> None:
        self.settings.set_values(**{"Just Show Only TrayIon": True})

        self.assertTrue(_should_start_hidden(self.settings, tray_available=True))
        self.assertFalse(_should_start_hidden(self.settings, tray_available=False))


if __name__ == "__main__":
    unittest.main()
