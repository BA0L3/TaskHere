import tempfile
import threading
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from Background import BackgroundRuntime, Notificate_Task, TrayIcon
from Database.Database1 import DataBase
from Settings import Settings


class BackgroundRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        root = Path(self.temporary_directory.name)
        self.database = DataBase(root / "tasks.json")
        self.settings = Settings(root / "settings.json")

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def make_info(deadline: datetime) -> list[float | str]:
        return [3.0] * 10 + [deadline.strftime(DataBase.DATE_FORMAT)]

    def test_deadline_notification_is_sent_once_per_task_deadline(self) -> None:
        deadline = datetime.now() + timedelta(minutes=10)
        self.database.new_task(self.make_info(deadline), "Soon", "")
        self.settings.set_values(TimeAlertBeforeDeadline=15)
        runtime = BackgroundRuntime(self.database, self.settings)

        with patch("Background.Notify_Task") as notify:
            runtime._check_deadline_alerts()
            runtime._check_deadline_alerts()

        notify.assert_called_once()
        self.assertIn("Soon", notify.call_args.args[0])

    def test_zero_deadline_alert_interval_disables_alerts(self) -> None:
        deadline = datetime.now() + timedelta(minutes=1)
        self.database.new_task(self.make_info(deadline), "Soon", "")
        self.settings.set_values(TimeAlertBeforeDeadline=0)
        runtime = BackgroundRuntime(self.database, self.settings)

        with patch("Background.Notify_Task") as notify:
            runtime._check_deadline_alerts()

        notify.assert_not_called()

    def test_detailed_toast_actions_update_open_and_complete_task(self) -> None:
        deadline = datetime.now() + timedelta(days=1)
        self.database.new_task(self.make_info(deadline), "Reminder", "Old note")
        self.settings.set_values(**{"Toast detail": "Detailed"})
        open_task = Mock()
        tasks_changed = Mock()
        runtime = BackgroundRuntime(
            self.database,
            self.settings,
            open_task_callback=open_task,
            tasks_changed_callback=tasks_changed,
        )

        with patch("Background.Notificate_Task") as notify:
            runtime._notify_top_task()

        notify.assert_called_once()
        self.assertEqual(
            notify.call_args.kwargs["language"],
            "Vie",
        )
        action_callback = notify.call_args.kwargs["on_action"]
        action_callback("change_and_launch", "Updated note")
        updated_task = self.database.get_task("Reminder")
        if updated_task is None:
            self.fail("The toast note action removed the task unexpectedly")
        self.assertEqual(updated_task["note"], "Updated note")
        open_task.assert_called_once_with("Reminder")
        tasks_changed.assert_called_once()

        action_callback("task_done", None)
        self.assertIsNone(self.database.get_task("Reminder"))
        self.assertEqual(tasks_changed.call_count, 2)

    def test_completing_recurring_task_keeps_it_for_next_occurrence(self) -> None:
        self.database.new_task(
            self.make_info(datetime.now() + timedelta(days=1)),
            "Daily reminder",
            "",
            "type_2",
            {"deadline_mode": "end_of_day"},
        )
        changed = Mock()
        runtime = BackgroundRuntime(
            self.database,
            self.settings,
            tasks_changed_callback=changed,
        )

        runtime._handle_toast_action("Daily reminder", "task_done", None)

        task = self.database.get_task("Daily reminder")
        self.assertIsNotNone(task)
        if task is None:
            self.fail("Completing a recurring task removed it from the database")
        self.assertEqual(task["completed_for"], datetime.now().date().isoformat())
        self.assertTrue(self.database.is_timed_out(task))
        changed.assert_called_once()

    def test_detailed_notification_dispatches_button_action_and_note(self) -> None:
        toaster = Mock()
        action_handler = Mock()
        with patch("Background.InteractableWindowsToaster", return_value=toaster):
            Notificate_Task(
                "Reminder",
                ["Deadline: tomorrow"],
                on_action=action_handler,
                language="Eng",
            )

        toast = toaster.show_toast.call_args.args[0]
        self.assertEqual(
            [button.arguments for button in toast.actions],
            [
                "action=submit",
                "action=launch",
                "action=change_and_launch",
                "action=task_done",
            ],
        )
        toast.on_activated(
            SimpleNamespace(
                arguments="action=change_and_launch",
                inputs={"change_note": "New note"},
            )
        )
        action_handler.assert_called_once_with(
            "change_and_launch", "New note"
        )

    def test_runtime_work_runs_outside_the_calling_thread(self) -> None:
        entered_refresh = threading.Event()
        release_refresh = threading.Event()

        def blocking_refresh() -> None:
            entered_refresh.set()
            release_refresh.wait(timeout=2)

        self.database.refresh_weights = blocking_refresh
        runtime = BackgroundRuntime(self.database, self.settings)
        try:
            with patch("Background.os.name", "posix"):
                runtime.start()
                self.assertTrue(entered_refresh.wait(timeout=1))
                worker = runtime._thread
                if worker is None:
                    self.fail("The background worker thread did not start")
                self.assertTrue(worker.is_alive())
        finally:
            release_refresh.set()
            runtime.stop()

    def test_tray_hide_menu_calls_hide_callback(self) -> None:
        hide = Mock()
        with patch("Background.pystray.Icon"):
            tray = TrayIcon(Mock(), hide, Mock())

        tray._hide(None, None)

        hide.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
