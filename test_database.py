import json
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from Database import DataBase


class DataBaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.path = Path(self.temporary_directory.name) / "tasks.json"
        self.database = DataBase(self.path)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    @staticmethod
    def make_info(score: float = 3) -> list[float | str]:
        deadline = datetime.now() + timedelta(days=30)
        return [score] * 10 + [deadline.strftime(DataBase.DATE_FORMAT)]

    def test_create_update_rename_and_remove_task(self) -> None:
        task = self.database.new_task(self.make_info(), "Example", "first note")
        created_at = task["created_at"]

        updated = self.database.update_task(
            "example", self.make_info(4), "updated note", new_name="Renamed"
        )
        self.assertEqual(updated["created_at"], created_at)
        self.assertEqual(updated["note"], "updated note")
        self.assertIsNone(self.database.get_task("Example"))
        self.assertIsNotNone(self.database.get_task("renamed"))

        self.database.remove_task("RENAMED")
        self.assertEqual(self.database.get_tasks(), [])

    def test_create_rejects_duplicate_names_case_insensitively(self) -> None:
        self.database.new_task(self.make_info(), "Example", "")
        with self.assertRaises(ValueError):
            self.database.new_task(self.make_info(), "example", "")

    def test_weight_calculation_does_not_mutate_input_scores(self) -> None:
        info = self.make_info()
        original_info = list(info)

        self.database.get_weight(info)

        self.assertEqual(info, original_info)

    def test_refresh_weights_recalculates_and_persists_values(self) -> None:
        task = self.database.new_task(self.make_info(), "Example", "")
        task["weight"] = -100
        self.database._write_tasks([task])

        self.database.refresh_weights()

        persisted_task = json.loads(self.path.read_text(encoding="utf-8"))[0]
        self.assertNotEqual(persisted_task["weight"], -100)
        self.assertAlmostEqual(
            persisted_task["weight"],
            self.database.get_weight(persisted_task["info"]),
            places=5,
        )

    def test_weight_calculation_rejects_non_finite_scores(self) -> None:
        info = self.make_info()
        info[0] = float("nan")

        with self.assertRaisesRegex(ValueError, "between 1 and 5"):
            self.database.get_weight(info)

    def test_create_rejects_past_deadline(self) -> None:
        info = self.make_info()
        info[10] = (datetime.now() - timedelta(days=1)).strftime(
            DataBase.DATE_FORMAT
        )

        with self.assertRaisesRegex(ValueError, "future"):
            self.database.new_task(info, "Expired", "")

    def test_clear_timed_out_tasks_preserves_active_tasks(self) -> None:
        expired_info = self.make_info()
        expired_info[10] = (datetime.now() - timedelta(minutes=1)).strftime(
            DataBase.DATE_FORMAT
        )
        expired = {
            "task_name": "Expired",
            "info": expired_info,
            "note": "",
            "created_at": datetime.now().strftime(DataBase.DATE_FORMAT),
            "weight": 0,
        }
        active = self.database.new_task(self.make_info(), "Active", "")
        self.database._write_tasks([expired, active])

        removed = self.database.clear_timed_out_tasks()

        self.assertEqual(removed, ["Expired"])
        self.assertEqual(
            [task["task_name"] for task in self.database.get_tasks()],
            ["Active"],
        )

    def test_reads_existing_task_name_and_name_fields(self) -> None:
        tasks = [
            {
                "task_name": "Existing format",
                "info": self.make_info(),
                "note": "",
                "created_at": "12/10/2026 13:09:22",
                "weight": 0,
            },
            {
                "name": "Earlier format",
                "info": self.make_info(),
                "note": "",
                "created_at": "12/10/2026 13:09:22",
                "weight": 0,
            },
        ]
        self.path.write_text(json.dumps(tasks), encoding="utf-8")

        names = {
            task.get("task_name", task.get("name"))
            for task in self.database.get_tasks()
        }

        self.assertEqual(names, {"Existing format", "Earlier format"})

    def test_invalid_json_is_reported_without_resetting_data(self) -> None:
        invalid_json = "{invalid"
        self.path.write_text(invalid_json, encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "invalid JSON"):
            self.database.get_tasks()

        self.assertEqual(self.path.read_text(encoding="utf-8"), invalid_json)


if __name__ == "__main__":
    unittest.main()
