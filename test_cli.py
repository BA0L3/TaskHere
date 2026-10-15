import io
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from Database import DataBase
from Settings import Settings
from cli import CLI
from config import WEIGHTS


class CLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.database = DataBase(root / "tasks.json")
        self.settings = Settings(root / "settings.json")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_tray_shutdown_event_allows_cli_to_exit(self) -> None:
        cli = CLI(self.database, WEIGHTS, self.settings)
        output = io.StringIO()

        with patch("builtins.input", return_value="help"), redirect_stdout(output):
            cli.stop_event.set()
            cli.run()

        self.assertIn("TasksHere CLI", output.getvalue())

    def test_auto_print_list_prints_tasks_on_startup(self) -> None:
        deadline = datetime.now() + timedelta(days=2)
        info = [3.0] * 10 + [deadline.strftime(DataBase.DATE_FORMAT)]
        self.database.new_task(info, "Example", "")
        self.settings.set_values(AutoPrintList=True)
        cli = CLI(self.database, WEIGHTS, self.settings)
        output = io.StringIO()

        with patch("builtins.input", return_value="exit"), redirect_stdout(output):
            cli.run()

        self.assertIn("Example", output.getvalue())

    def test_settings_command_updates_reminder_interval(self) -> None:
        cli = CLI(self.database, WEIGHTS, self.settings)

        with patch("builtins.input", side_effect=["RemindTask", "5"]):
            cli.configure_settings()

        self.assertEqual(self.settings.RemindTask, 5)

    def test_settings_command_updates_language(self) -> None:
        cli = CLI(self.database, WEIGHTS, self.settings)

        with patch("builtins.input", side_effect=["Language", "Eng"]):
            cli.configure_settings()

        self.assertEqual(self.settings.Language, "Eng")


if __name__ == "__main__":
    unittest.main()
