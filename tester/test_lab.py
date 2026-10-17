import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from Database.Database1 import DataBase
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from lab import _prompt_deadline_fields, prompt_deadline


class DeadlinePromptTests(unittest.TestCase):
    @staticmethod
    def fields_for(deadline: datetime) -> tuple[str, ...]:
        return (
            f"{deadline.year:04d}",
            f"{deadline.month:02d}",
            f"{deadline.day:02d}",
            f"{deadline.hour:02d}",
            f"{deadline.minute:02d}",
            f"{deadline.second:02d}",
        )

    def test_retries_invalid_and_past_deadlines(self) -> None:
        past = datetime.now() - timedelta(days=1)
        future = datetime.now() + timedelta(days=2)
        with patch(
            "lab._prompt_deadline_fields",
            side_effect=[
                ("2030", "2", "30", "12", "0", "0"),
                self.fields_for(past),
                self.fields_for(future),
            ],
        ):
            self.assertEqual(
                prompt_deadline(DataBase.DATE_FORMAT),
                future.strftime(DataBase.DATE_FORMAT),
            )

    def test_cancel_returns_none(self) -> None:
        with patch("lab._prompt_deadline_fields", return_value=None):
            self.assertIsNone(prompt_deadline(DataBase.DATE_FORMAT))

    def test_editor_limits_each_field_and_advances_with_enter(self) -> None:
        with create_pipe_input() as test_input:
            test_input.send_text("20301\r123\r245\r456\r567\r678\r")
            values = _prompt_deadline_fields(
                input=test_input,
                output=DummyOutput(),
            )

        self.assertEqual(values, ("2030", "12", "24", "45", "56", "67"))
        valid_fields = ("2030", "1", "2", "4", "5", "6")
        with patch("lab._prompt_deadline_fields", return_value=valid_fields):
            deadline = prompt_deadline(DataBase.DATE_FORMAT)
        self.assertEqual(deadline, "02/01/2030 04:05:06")


if __name__ == "__main__":
    unittest.main()
