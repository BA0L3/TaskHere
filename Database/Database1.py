import json
import logging
import math
import os
import tempfile
import threading
from calendar import monthrange
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class DataBase_TaskType_1:
    DATE_FORMAT = "%d/%m/%Y %H:%M:%S"
    TIME_FORMAT = "%H:%M:%S"
    TASK_TYPES = {"type_1", "type_2", "type_3", "type_4", "type_5"}
    RECURRING_TYPES = {"type_2", "type_3", "type_4", "type_5"}
    VALUES = (0.25, 0.2, 0.15, 0.15, 0.1, -0.05, -0.05, -0.02, -0.03, 1.0)

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path)
        self._lock = threading.RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists() or self.path.stat().st_size == 0:
            self._write_tasks([])

    @staticmethod
    def _task_name(task: dict[str, Any]) -> str:
        name = task.get("task_name", task.get("name"))
        if not isinstance(name, str):
            raise ValueError("Task is missing a valid task_name.")
        return name

    def _read_tasks(self) -> list[dict[str, Any]]:
        try:
            with self.path.open("r", encoding="utf-8") as file:
                tasks = json.load(file)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Tasks file contains invalid JSON: {self.path}") from exc

        if not isinstance(tasks, list):
            raise ValueError("Tasks file must contain a JSON list.")
        for task in tasks:
            if not isinstance(task, dict):
                raise ValueError("Every task entry must be a JSON object.")
            self._task_name(task)
            task.setdefault("task_type", "type_1")
            if (
                not isinstance(task["task_type"], str)
                or task["task_type"] not in self.TASK_TYPES
            ):
                raise ValueError(
                    f"Task {self._task_name(task)!r} has an unsupported type."
                )
            if task["task_type"] in self.RECURRING_TYPES:
                task["schedule"] = self._normalize_schedule(
                    task["task_type"], task.get("schedule", {})
                )
        return tasks

    def _write_tasks(self, tasks: list[dict[str, Any]]) -> None:
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
                json.dump(tasks, file, indent=4, ensure_ascii=False)
                file.write("\n")
            os.replace(temporary_path, self.path)
        except OSError:
            if temporary_path and os.path.exists(temporary_path):
                try:
                    os.unlink(temporary_path)
                except OSError:
                    logger.exception(
                        "Could not remove temporary tasks file %s",
                        temporary_path,
                    )
            raise

    def get_tasks(self) -> list[dict[str, Any]]:
        with self._lock:
            tasks = [
                self._task_for_read(task, datetime.now())
                for task in self._read_tasks()
            ]
            return sorted(tasks, key=lambda task: task["weight"], reverse=True)

    def get_task(self, task_name: str) -> dict[str, Any] | None:
        with self._lock:
            target = task_name.casefold()
            task = next(
                (item for item in self._read_tasks()
                 if self._task_name(item).casefold() == target),
                None,
            )
            return self._task_for_read(task, datetime.now()) if task else None

    def new_task(
        self,
        info: list[Any],
        task_name: str,
        note: str,
        task_type: str = "type_1",
        schedule: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            name = task_name.strip()
            if not name:
                raise ValueError("Task name cannot be blank.")
            task_type, schedule = self._validate_task_details(
                info, task_type, schedule
            )

            tasks = self._read_tasks()
            if any(
                self._task_name(task).casefold() == name.casefold()
                for task in tasks
            ):
                raise ValueError(f'A task named "{name}" already exists.')

            task = {
                "task_name": name,
                "info": list(info),
                "note": note,
                "task_type": task_type,
                "created_at": datetime.now().strftime(self.DATE_FORMAT),
            }
            if schedule is not None:
                task["schedule"] = schedule
            task["weight"] = self._task_weight(task, datetime.now())
            tasks.append(task)
            self.sort_tasks_and_update(tasks)
            logger.info("Created task %r", name)
            return self._task_for_read(task, datetime.now())

    def update_task(
        self,
        task_name: str,
        new_info: list[Any],
        new_note: str,
        new_name: str | None = None,
        task_type: str | None = None,
        schedule: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            updated_name = task_name if new_name is None else new_name.strip()
            if not updated_name:
                raise ValueError("Task name cannot be blank.")
            tasks = self._read_tasks()
            task = next(
                (
                    item for item in tasks
                    if self._task_name(item).casefold() == task_name.casefold()
                ),
                None,
            )
            if task is None:
                raise KeyError(f'Task "{task_name}" was not found.')
            updated_type = task_type or task["task_type"]
            updated_schedule = (
                schedule
                if task_type is not None or schedule is not None
                else task.get("schedule")
            )
            updated_type, updated_schedule = self._validate_task_details(
                new_info, updated_type, updated_schedule
            )
            if any(
                item is not task
                and self._task_name(item).casefold() == updated_name.casefold()
                for item in tasks
            ):
                raise ValueError(f'A task named "{updated_name}" already exists.')

            task["task_name"] = updated_name
            task.pop("name", None)
            task["info"] = list(new_info)
            task["note"] = new_note
            if (
                updated_type != task.get("task_type")
                or updated_schedule != task.get("schedule")
            ):
                task.pop("completed_for", None)
            task["task_type"] = updated_type
            task.pop("schedule", None)
            if updated_schedule is not None:
                task["schedule"] = updated_schedule
            task["weight"] = self._task_weight(task, datetime.now())
            self.sort_tasks_and_update(tasks)
            logger.info("Updated task %r", updated_name)
            return self._task_for_read(task, datetime.now())

    def remove_task(self, task_name: str) -> None:
        with self._lock:
            tasks = self._read_tasks()
            remaining = [
                task for task in tasks
                if self._task_name(task).casefold() != task_name.casefold()
            ]
            if len(remaining) == len(tasks):
                raise KeyError(f'Task "{task_name}" was not found.')
            self.sort_tasks_and_update(remaining)
            logger.info("Removed task %r", task_name)

    def sort_tasks_and_update(self, tasks: list[dict[str, Any]]) -> None:
        with self._lock:
            now = datetime.now()
            for task in tasks:
                task["weight"] = self._task_weight(task, now)
            tasks.sort(key=lambda task: task["weight"], reverse=True)
            self._write_tasks(tasks)

    def refresh_weights(self) -> None:
        with self._lock:
            tasks = self._read_tasks()
            self.sort_tasks_and_update(tasks)

    @classmethod
    def is_timed_out(
        cls, task: dict[str, Any], now: datetime | None = None
    ) -> bool:
        current_time = now or datetime.now()
        task_type = task.get("task_type", "type_1")
        if task_type in cls.RECURRING_TYPES:
            schedule = cls._normalize_schedule(task_type, task.get("schedule", {}))
            today = current_time.date()
            if not cls._is_scheduled_date(task_type, schedule, today):
                return True
            if task.get("completed_for") == today.isoformat():
                return True
            deadline = cls._deadline_for(today, schedule)
            return current_time >= deadline
        deadline = datetime.strptime(task["info"][10], cls.DATE_FORMAT)
        return deadline <= current_time

    def clear_timed_out_tasks(self) -> list[str]:
        with self._lock:
            tasks = self._read_tasks()
            current_time = datetime.now()
            expired_names = [
                self._task_name(task)
                for task in tasks
                if task.get("task_type", "type_1") == "type_1"
                and self.is_timed_out(task, current_time)
            ]
            if not expired_names:
                return []

            expired_set = {name.casefold() for name in expired_names}
            remaining = [
                task
                for task in tasks
                if self._task_name(task).casefold() not in expired_set
            ]
            self.sort_tasks_and_update(remaining)
            logger.info("Cleared %d timed-out tasks", len(expired_names))
            return expired_names

    def mark_task_done(self, task_name: str) -> None:
        with self._lock:
            tasks = self._read_tasks()
            task = next(
                (item for item in tasks
                 if self._task_name(item).casefold() == task_name.casefold()),
                None,
            )
            if task is None:
                raise KeyError(f'Task "{task_name}" was not found.')
            if task["task_type"] == "type_1":
                self.remove_task(task_name)
                return
            task["completed_for"] = datetime.now().date().isoformat()
            self.sort_tasks_and_update(tasks)

    @classmethod
    def _normalize_schedule(
        cls, task_type: str, schedule: dict[str, Any]
    ) -> dict[str, Any]:
        if not isinstance(schedule, dict):
            raise ValueError("A recurring task needs a valid schedule.")
        normalized: dict[str, Any] = {}
        mode = schedule.get("deadline_mode", "end_of_day")
        if not isinstance(mode, str) or mode not in {"end_of_day", "specific"}:
            raise ValueError("Deadline mode must be end_of_day or specific.")
        normalized["deadline_mode"] = mode
        raw_time = schedule.get("deadline_time", "23:59:59")
        if not isinstance(raw_time, str):
            raise ValueError("Recurring deadline time must be a string.")
        try:
            parsed_time = datetime.strptime(raw_time, cls.TIME_FORMAT).time()
        except ValueError as exc:
            raise ValueError(
                f"Recurring deadline time must use {cls.TIME_FORMAT}."
            ) from exc
        normalized["deadline_time"] = (
            "23:59:59" if mode == "end_of_day" else parsed_time.strftime("%H:%M:%S")
        )

        if task_type == "type_3":
            weekday = schedule.get("weekday")
            if (
                not isinstance(weekday, int)
                or isinstance(weekday, bool)
                or not 0 <= weekday <= 6
            ):
                raise ValueError("Weekly tasks need a weekday from 0 (Mon) to 6 (Sun).")
            normalized["weekday"] = weekday
        elif task_type == "type_4":
            day = schedule.get("day")
            if (
                not isinstance(day, int)
                or isinstance(day, bool)
                or not 1 <= day <= 31
            ):
                raise ValueError("Monthly tasks need a day from 1 to 31.")
            normalized["day"] = day
        elif task_type == "type_5":
            month, day = schedule.get("month"), schedule.get("day")
            if (
                not isinstance(month, int)
                or isinstance(month, bool)
                or not 1 <= month <= 12
                or not isinstance(day, int)
                or isinstance(day, bool)
                or not 1 <= day <= 31
            ):
                raise ValueError("Yearly tasks need a valid month and day.")
            try:
                date(2000, month, day)
            except ValueError as exc:
                raise ValueError("Yearly task date is not valid.") from exc
            normalized.update(month=month, day=day)
        return normalized

    def _validate_task_details(
        self,
        info: list[Any],
        task_type: str,
        schedule: dict[str, Any] | None,
    ) -> tuple[str, dict[str, Any] | None]:
        if not isinstance(task_type, str) or task_type not in self.TASK_TYPES:
            raise ValueError("Unsupported task type.")
        self.get_weight(info)
        if task_type == "type_1":
            self._validate_future_deadline(info)
            return task_type, None
        return task_type, self._normalize_schedule(task_type, schedule or {})

    @classmethod
    def _task_for_read(
        cls, task: dict[str, Any], now: datetime
    ) -> dict[str, Any]:
        result = dict(task)
        result["info"] = list(task["info"])
        if result.get("task_type", "type_1") in cls.RECURRING_TYPES:
            schedule = cls._normalize_schedule(
                result["task_type"], result.get("schedule", {})
            )
            next_date = cls._next_occurrence(
                result["task_type"],
                schedule,
                now,
                result.get("completed_for"),
            )
            result["info"][10] = cls._deadline_for(
                next_date, schedule
            ).strftime(cls.DATE_FORMAT)
            result["weight"] = cls._weight_for_info(result["info"], now)
        else:
            result["weight"] = cls._weight_for_info(result["info"], now)
        return result

    @classmethod
    def _task_weight(cls, task: dict[str, Any], now: datetime) -> float:
        task_type = task.get("task_type", "type_1")
        info = list(task["info"])
        if task_type in cls.RECURRING_TYPES:
            schedule = cls._normalize_schedule(task_type, task.get("schedule", {}))
            occurrence = cls._next_occurrence(
                task_type, schedule, now, task.get("completed_for")
            )
            info[10] = cls._deadline_for(occurrence, schedule).strftime(cls.DATE_FORMAT)
        return cls._weight_for_info(info, now)

    @classmethod
    def _weight_for_info(cls, info: list[Any], now: datetime) -> float:
        if len(info) != len(cls.VALUES) + 1:
            raise ValueError("Task info must contain 10 scores and one deadline.")
        try:
            scores = [float(value) for value in info[:len(cls.VALUES)]]
        except (TypeError, ValueError) as exc:
            raise ValueError("Task scores must all be numeric.") from exc
        if any(
            not math.isfinite(score) or score < 1 or score > 5 for score in scores
        ):
            raise ValueError("Task scores must be between 1 and 5.")
        if not isinstance(info[10], str):
            raise ValueError("Task deadline must be a date string.")
        try:
            deadline = datetime.strptime(info[10], cls.DATE_FORMAT)
        except ValueError as exc:
            raise ValueError(
                f"Deadline must use the format {cls.DATE_FORMAT}."
            ) from exc
        time_left = (deadline - now).total_seconds() / 3600
        scores[1] += 1 / (1 + (time_left / 24) ** 2)
        return sum(weight * score for weight, score in zip(cls.VALUES, scores))

    @classmethod
    def _is_scheduled_date(
        cls, task_type: str, schedule: dict[str, Any], day: date
    ) -> bool:
        if task_type == "type_2":
            return True
        if task_type == "type_3":
            return day.weekday() == schedule["weekday"]
        if task_type == "type_4":
            return day.day == min(schedule["day"], monthrange(day.year, day.month)[1])
        return (
            day.month == schedule["month"]
            and day.day == min(schedule["day"], monthrange(day.year, day.month)[1])
        )

    @classmethod
    def _next_occurrence(
        cls,
        task_type: str,
        schedule: dict[str, Any],
        now: datetime,
        completed_for: str | None = None,
    ) -> date:
        today = now.date()
        if (
            cls._is_scheduled_date(task_type, schedule, today)
            and completed_for != today.isoformat()
        ):
            deadline = cls._deadline_for(today, schedule)
            if now < deadline:
                return today
        candidate = today + timedelta(days=1)
        for _ in range(367):
            if cls._is_scheduled_date(task_type, schedule, candidate):
                return candidate
            candidate += timedelta(days=1)
        raise ValueError("Could not calculate the next recurring task occurrence.")

    @classmethod
    def _deadline_for(cls, day: date, schedule: dict[str, Any]) -> datetime:
        parsed_time = datetime.strptime(
            schedule["deadline_time"], cls.TIME_FORMAT
        ).time()
        return datetime.combine(day, parsed_time)

    def get_weight(self, info: list[Any]) -> float:
        return self._weight_for_info(info, datetime.now())

    def _validate_future_deadline(self, info: list[Any]) -> None:
        deadline = datetime.strptime(info[10], self.DATE_FORMAT)
        if deadline <= datetime.now():
            raise ValueError("Deadline must be in the future.")

    def calculate_urgency(self, initial_urgency: float, deadline: str, k: int = 2) -> float:
        try:
            deadline_time = datetime.strptime(deadline, self.DATE_FORMAT)
        except ValueError as exc:
            raise ValueError(
                f"Deadline must use the format {self.DATE_FORMAT}."
            ) from exc

        time_left = (deadline_time - datetime.now()).total_seconds() / 3600
        half_day = 24
        return initial_urgency + 1 / (1 + (time_left / half_day) ** k)


DataBase = DataBase_TaskType_1
