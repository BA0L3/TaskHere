from datetime import datetime

from prompt_toolkit.application import Application
from prompt_toolkit.input import Input
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.key_binding.key_processor import KeyPressEvent
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.data_structures import Point
from prompt_toolkit.output import Output


_DEADLINE_FIELDS = ("yyyy", "mm", "dd", "hh", "mm", "ss")
_DEADLINE_LIMITS = (4, 2, 2, 2, 2, 2)
_DEADLINE_SEPARATORS = (" ", " ", " - ", ":", ":")


def _prompt_deadline_fields(
    input: Input | None = None,
    output: Output | None = None,
) -> tuple[str, ...] | None:
    values = ["" for _ in _DEADLINE_FIELDS]
    active_field = 0
    message = "Enter = next field | Backspace = edit | Esc = cancel"

    def get_pattern() -> str:
        pattern = "    "
        for index, field in enumerate(_DEADLINE_FIELDS):
            value = values[index]
            pattern += f"[{value}{field[len(value):]}]"
            if index < len(_DEADLINE_SEPARATORS):
                pattern += _DEADLINE_SEPARATORS[index]
        return pattern

    def get_text() -> str:
        return (
            "Enter Deadline for this task:\n"
            f"{get_pattern()}\n"
            f"{message}"
        )

    def get_cursor_position() -> Point:
        pattern_prefix = "    "
        for index in range(active_field):
            pattern_prefix += (
                f"[{_DEADLINE_FIELDS[index]}]"
                f"{_DEADLINE_SEPARATORS[index]}"
            )
        return Point(
            x=len(pattern_prefix) + 1 + len(values[active_field]),
            y=1,
        )

    key_bindings = KeyBindings()

    def insert_digit(event: KeyPressEvent, digit: str) -> None:
        nonlocal message
        if len(values[active_field]) < _DEADLINE_LIMITS[active_field]:
            values[active_field] += digit
            message = "Enter = next field | Backspace = edit | Esc = cancel"
            event.app.invalidate()

    for digit in "0123456789":

        @key_bindings.add(digit)
        def _insert_digit(event: KeyPressEvent, digit: str = digit) -> None:
            insert_digit(event, digit)

    @key_bindings.add("backspace")
    def _backspace(event: KeyPressEvent) -> None:
        nonlocal active_field, message
        if values[active_field]:
            values[active_field] = values[active_field][:-1]
        elif active_field > 0:
            active_field -= 1
            values[active_field] = values[active_field][:-1]
        message = "Enter = next field | Backspace = edit | Esc = cancel"
        event.app.invalidate()

    @key_bindings.add("enter")
    def _advance(event: KeyPressEvent) -> None:
        nonlocal active_field, message
        value = values[active_field]
        if not value:
            message = "This field is required."
        elif active_field == 0 and len(value) != _DEADLINE_LIMITS[0]:
            message = "Enter a 4-digit year."
        elif active_field == len(_DEADLINE_FIELDS) - 1:
            event.app.exit(result=tuple(values))
            return
        else:
            active_field += 1
            message = "Enter = next field | Backspace = edit | Esc = cancel"
        event.app.invalidate()

    @key_bindings.add("escape")
    @key_bindings.add("c-c")
    def _cancel(event: KeyPressEvent) -> None:
        event.app.exit(result=None)

    control = FormattedTextControl(
        text=get_text,
        get_cursor_position=get_cursor_position,
    )
    application: Application[tuple[str, ...] | None] = Application(
        layout=Layout(Window(control)),
        key_bindings=key_bindings,
        input=input,
        output=output,
        full_screen=False,
        erase_when_done=False,
    )
    return application.run()


def prompt_deadline(date_format: str) -> str | None:
    while True:
        values = _prompt_deadline_fields()
        if values is None:
            return None

        try:
            year, month, day, hour, minute, second = (
                value.zfill(2) if index else value
                for index, value in enumerate(values)
            )
            deadline = datetime.strptime(
                f"{year}-{month}-{day} {hour}:{minute}:{second}",
                "%Y-%m-%d %H:%M:%S",
            )
        except (TypeError, ValueError):
            print("Invalid deadline. Enter a valid date and time.")
            continue

        if deadline <= datetime.now():
            print("Deadline must be in the future.")
            continue
        return deadline.strftime(date_format)
