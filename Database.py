import json
import logging
import math
import os
import tempfile
import threading
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class DataBase:
    DATE_FORMAT = "%d/%m/%Y %H:%M:%S"
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
            tasks = self._read_tasks()
            for task in tasks:
                task["weight"] = self.get_weight(task["info"])
            tasks.sort(
                key=lambda task: self.get_weight(task["info"]), reverse=True
            )
            return tasks

    def get_task(self, task_name: str) -> dict[str, Any] | None:
        with self._lock:
            target = task_name.casefold()
            return next(
                (
                    task for task in self._read_tasks()
                    if self._task_name(task).casefold() == target
                ),
                None,
            )

    def new_task(self, info: list[Any], task_name: str, note: str) -> dict[str, Any]:
        with self._lock:
            name = task_name.strip()
            if not name:
                raise ValueError("Task name cannot be blank.")
            self.get_weight(info)
            self._validate_future_deadline(info)

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
                "created_at": datetime.now().strftime(self.DATE_FORMAT),
                "weight": self.get_weight(info),
            }
            tasks.append(task)
            self.sort_tasks_and_update(tasks)
            logger.info("Created task %r", name)
            return task

    def update_task(
        self,
        task_name: str,
        new_info: list[Any],
        new_note: str,
        new_name: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            self.get_weight(new_info)
            self._validate_future_deadline(new_info)
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
            task["weight"] = self.get_weight(new_info)
            self.sort_tasks_and_update(tasks)
            logger.info("Updated task %r", updated_name)
            return task

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
            tasks.sort(key=lambda task: self.get_weight(task["info"]), reverse=True)
            for task in tasks:
                task["weight"] = self.get_weight(task["info"])
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
        deadline = datetime.strptime(task["info"][10], cls.DATE_FORMAT)
        return deadline <= current_time

    def clear_timed_out_tasks(self) -> list[str]:
        with self._lock:
            tasks = self._read_tasks()
            current_time = datetime.now()
            expired_names = [
                self._task_name(task)
                for task in tasks
                if self.is_timed_out(task, current_time)
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

    def get_weight(self, info: list[Any]) -> float:
        if len(info) != len(self.VALUES) + 1:
            raise ValueError("Task info must contain 10 scores and one deadline.")
        try:
            scores = [float(value) for value in info[:len(self.VALUES)]]
        except (TypeError, ValueError) as exc:
            raise ValueError("Task scores must all be numeric.") from exc
        if any(not math.isfinite(score) or score < 1 or score > 5 for score in scores):
            raise ValueError("Task scores must be between 1 and 5.")
        if not isinstance(info[10], str):
            raise ValueError("Task deadline must be a date string.")

        urgency = self.calculate_urgency(
            scores[1],
            info[10],
        )
        scores[1] = urgency
        return sum(weight * score for weight, score in zip(self.VALUES, scores))

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
