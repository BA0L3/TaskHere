import logging
import os
import queue
import threading
from typing import Any

from prompt_toolkit import prompt

from Background import _auto_start_of, _auto_start_on
from Database import DataBase
from Settings import Settings
from lab import prompt_deadline


logger = logging.getLogger(__name__)


class CLI:
    def __init__(
        self,
        database: DataBase,
        weights_name: list[str],
        settings: Settings | None = None,
        stop_event: threading.Event | None = None,
    ) -> None:
        if len(weights_name) != 11:
            raise ValueError("The CLI needs 10 score labels and a deadline label.")
        self.db = database
        self.weights_name = weights_name
        self.settings = settings if settings is not None else Settings()
        if settings is None and self.settings.recovery_message:
            print(f"Warning: {self.settings.recovery_message}")
        self.stop_event = stop_event or threading.Event()
        self._commands: queue.Queue[str | None] = queue.Queue()
        self._input_ready = threading.Event()
        self.running = True
        self.commands = {
            "add": self.add_task,
            "list": self.list_tasks,
            "update": self.update_task,
            "remove": self.remove_task,
            "help": self.show_help,
            "settings": self.configure_settings,
            "exit": self.exit_cli,
            "quit": self.exit_cli,
        }

    def run(self) -> None:
        print("TasksHere CLI. Type 'help' to see available commands.")
        if self.settings.AutoPrintList:
            try:
                self.list_tasks()
            except (OSError, ValueError, KeyError) as exc:
                logger.exception("Could not print tasks at startup")
                print(f"Could not print tasks at startup: {exc}")

        input_thread = threading.Thread(
            target=self._read_commands,
            name="taskshere-console-input",
            daemon=True,
        )
        input_thread.start()
        self._input_ready.set()
        while self.running and not self.stop_event.is_set():
            try:
                command_line = self._commands.get(timeout=0.2)
            except queue.Empty:
                continue
            if command_line is None:
                print()
                self.exit_cli()
                break

            command = command_line.strip().casefold()
            if not command:
                self._input_ready.set()
                continue
            action = self.commands.get(command)
            if action is None:
                print(f'Unknown command "{command}". Type "help" for commands.')
                self._input_ready.set()
                continue
            logger.info("Command selected: %s", command)
            try:
                action()
            except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
                logger.exception("Command %r failed", command)
                print(f"Could not complete '{command}': {exc}")
            finally:
                self._input_ready.set()
        self._input_ready.set()

    def _read_commands(self) -> None:
        while not self.stop_event.is_set():
            self._input_ready.wait()
            if self.stop_event.is_set():
                return
            self._input_ready.clear()
            try:
                command = input("\ntasks> ")
            except (EOFError, KeyboardInterrupt):
                self._commands.put(None)
                return
            except Exception as exc:
                logger.exception("Could not read a CLI command")
                print(f"Could not read CLI input: {exc}")
                self._commands.put(None)
                return
            self._commands.put(command)

    def exit_cli(self) -> None:
        print("Exiting CLI...")
        self.running = False
        self.stop_event.set()

    def show_from_tray(self) -> None:
        self.settings.show_console()
        print("\nTasksHere is active in this console. Return here to continue.")

    def show_help(self) -> None:
        print(
            "\nCommands:\n"
            "  add     Create a task\n"
            "  list    Show tasks, sorted by priority\n"
            "  update  Update a task's scores, deadline, and note\n"
            "  remove  Delete a task\n"
            "  settings View or change application settings\n"
            "  help    Show this help\n"
            "  exit    Close the CLI"
        )

    def configure_settings(self) -> None:
        for name in Settings.DEFAULTS:
            value = getattr(self.settings, name)
            if isinstance(value, bool):
                display_value = "on" if value else "off"
            elif isinstance(value, str):
                display_value = value
            else:
                display_value = f"{value} minute(s)"
            print(f"  {name}: {display_value}")

        requested_name = input(
            "Setting to change (press Enter to cancel): "
        ).strip().casefold()
        setting_name = next(
            (
                name for name in Settings.DEFAULTS
                if name.casefold() == requested_name
            ),
            None,
        )
        if setting_name is None:
            print("Settings unchanged.")
            return

        current_value = getattr(self.settings, setting_name)
        if isinstance(current_value, bool):
            raw_value = input(f"Enable {setting_name}? (y/N): ").strip().casefold()
            if raw_value not in {"y", "yes", "n", "no"}:
                print("Settings unchanged.")
                return
            new_value: bool | int | str = raw_value in {"y", "yes"}
        elif isinstance(current_value, str):
            choices = Settings.OPTIONS[setting_name]
            print(f"Available values: {', '.join(choices)}")
            raw_value = input(f"New value for {setting_name}: ").strip()
            if raw_value not in choices:
                print("Settings unchanged.")
                return
            new_value = raw_value
        else:
            if setting_name == "TimeAlertBeforeDeadline":
                prompt_text = "Alert lead time in minutes (0 disables alerts): "
            elif setting_name == "RemindTask":
                prompt_text = "Reminder interval in minutes (0 = startup only): "
            else:
                prompt_text = "Refresh interval in minutes (0 = startup only): "
            raw_value = input(prompt_text).strip()
            try:
                new_value = int(raw_value)
            except ValueError:
                print("Enter a whole number of minutes.")
                return
            if new_value < 0:
                print("The interval cannot be negative.")
                return

        if new_value == current_value:
            print("Settings unchanged.")
            return

        try:
            self.settings.set_values(**{setting_name: new_value})
        except OSError as exc:
            logger.exception("Could not save setting %s", setting_name)
            print(f"Could not save setting: {exc}")
            return

        if setting_name == "auto_start" and os.name == "nt":
            try:
                if new_value:
                    _auto_start_on()
                else:
                    _auto_start_of()
            except OSError as exc:
                try:
                    self.settings.set_auto_start(not new_value)
                except OSError as rollback_error:
                    logger.exception("Could not roll back the auto_start setting")
                    print(
                        "Windows auto-start could not be updated, and the "
                        f"settings file could not be rolled back: {rollback_error}"
                    )
                logger.exception("Could not update Windows auto-start")
                print(f"Could not update Windows auto-start: {exc}")
                return

        print(f"{setting_name} updated.")

    def list_tasks(self) -> None:
        tasks = self.db.get_tasks()
        if not tasks:
            print("No tasks found.")
            return

        print()
        for index, task in enumerate(tasks, start=1):
            name = task.get("task_name", task.get("name", "Unnamed task"))
            print(
                f"{index}. {name} | priority: {task['weight']:.2f} | "
                f"deadline: {task['info'][10]}"
            )
            if task.get("note"):
                print(f"   Note: {task['note']}")

    def _read_task_details(
        self, existing: dict[str, Any] | None = None
    ) -> tuple[list[Any], str, str] | None:
        name = input("Task name: ").strip()
        if name.casefold() in {"exit", "cancel"}:
            print("Task entry cancelled.")
            return None
        if not name:
            print("Task name cannot be blank.")
            return None
        if existing is None and self.db.get_task(name) is not None:
            print(f'A task named "{name}" already exists; use "update" to edit it.')
            return None

        scores: list[float] = []
        for label in self.weights_name[:10]:
            while True:
                raw_score = input(f"{label} (1-5): ").strip()
                if raw_score.casefold() in {"exit", "cancel"}:
                    print("Task entry cancelled.")
                    return None
                try:
                    score = float(raw_score)
                except ValueError:
                    print("Enter a number from 1 to 5.")
                    continue
                if not 1 <= score <= 5:
                    print("Enter a number from 1 to 5.")
                    continue
                scores.append(score)
                break

        deadline = prompt_deadline(DataBase.DATE_FORMAT)
        if deadline is None:
            print("Task entry cancelled.")
            return None

        print('Enter a note; press "Escape" then "Enter" when finished.')
        note = prompt("Note: ", multiline=True)
        return scores + [deadline], name, note

    def add_task(self) -> None:
        details = self._read_task_details()
        if details is None:
            return
        info, name, note = details
        self.db.new_task(info, name, note)
        print(f'Task "{name}" added.')

    def update_task(self) -> None:
        name = input("Task name to update: ").strip()
        task = self.db.get_task(name) if name else None
        if task is None:
            print(f'Task "{name}" was not found.')
            return

        details = self._read_task_details(existing=task)
        if details is None:
            return
        info, new_name, note = details
        if new_name.casefold() != name.casefold() and self.db.get_task(new_name):
            print(f'A task named "{new_name}" already exists.')
            return
        self.db.update_task(name, info, note, new_name=new_name)
        print(f'Task "{new_name}" updated.')

    def remove_task(self) -> None:
        name = input("Task name to remove: ").strip()
        if self.db.get_task(name) is None:
            print(f'Task "{name}" was not found.')
            return
        confirmation = input(f'Delete "{name}"? (y/N): ').strip().casefold()
        if confirmation not in {"y", "yes"}:
            print("Removal cancelled.")
            return
        self.db.remove_task(name)
        print(f'Task "{name}" removed.')


if __name__ == "__main__":
    from main import main

    raise SystemExit(main())
