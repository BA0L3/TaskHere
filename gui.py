from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Any

from config import METADATA

from PySide6.QtCore import QDate, QDateTime, QTime, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QColor, QTextCharFormat, QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateTimeEdit,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from Database import DataBase
from Settings import Settings
from i18n import colors, score_label, text
from config import ICON_FILE


logger = logging.getLogger(__name__)
TASK_TYPE_TEXT_KEYS = {
    "type_1": "type_deadline",
    "type_2": "type_daily",
    "type_3": "type_weekly",
    "type_4": "type_monthly",
    "type_5": "type_yearly",
}
TASK_TYPE_FILTER_TEXT_KEYS = {
    "type_2": "filter_daily",
    "type_3": "filter_weekly",
    "type_4": "filter_monthly",
    "type_5": "filter_yearly",
}


class PaletteComboBox(QComboBox):
    def __init__(
        self,
        palette: dict[str, str],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._popup_palette = palette.copy()
        self._configure_popup_view()

    def _configure_popup_view(self) -> None:
        view = self.view()
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.setLineWidth(0)
        view.setMidLineWidth(0)

    def set_popup_palette(self, palette: dict[str, str]) -> None:
        self._popup_palette = palette.copy()

    def showPopup(self) -> None:
        self._configure_popup_view()
        super().showPopup()
        popup_frame = self.view().window()
        popup_frame.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        popup_frame.setStyleSheet(
            "QFrame {"
            f"background: {self._popup_palette['surface']};"
            "border: none;"
            "}"
        )
        popup_frame.update()


class TaskDialog(QDialog):
    def __init__(
        self,
        weights_name: list[str],
        task: dict[str, Any] | None = None,
        language: str = "Vie",
        mode: str = "Light",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._task = task
        self.language = language
        palette = colors(mode)
        self.setStyleSheet(
            "QDialog {"
            f"background:{palette['window']}; color:{palette['text']};"
            "}"
        )
        self.setWindowTitle(
            text("task_dialog_edit" if task else "task_dialog_add", language)
        )
        self.setMinimumWidth(470)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(text("name_example", language))
        form.addRow(text("task_name", language), self.name_input)

        self.task_type_input = PaletteComboBox(palette)
        self.task_type_input.addItem(text("type_deadline", language), "type_1")
        self.task_type_input.addItem(text("type_daily", language), "type_2")
        self.task_type_input.addItem(text("type_weekly", language), "type_3")
        self.task_type_input.addItem(text("type_monthly", language), "type_4")
        self.task_type_input.addItem(text("type_yearly", language), "type_5")
        form.addRow(text("task_type", language), self.task_type_input)

        self.score_inputs: list[QDoubleSpinBox] = []
        self.setWindowIcon(QIcon(str(ICON_FILE)))
        for label in weights_name[:10]:
            score = QDoubleSpinBox()
            score.setRange(1.0, 5.0)
            score.setSingleStep(0.5)
            score.setDecimals(1)
            score.setValue(3.0)
            self.score_inputs.append(score)
            form.addRow(score_label(label, language), score)

        self.deadline_input = QDateTimeEdit()
        self.deadline_input.setCalendarPopup(True)
        self.deadline_input.setDisplayFormat("dd/MM/yyyy HH:mm:ss")
        self.deadline_input.setDateTime(QDateTime.currentDateTime().addDays(1))
        calendar = self.deadline_input.calendarWidget()
        calendar.setStyleSheet(
            f"""
            QCalendarWidget QWidget {{
                background-color: {palette['time_board']};
                color: {palette['text']};
            }}
            QCalendarWidget QTableView {{
                background-color: {palette['time_board']};
                color: {palette['text']};
                alternate-background-color: {palette['header']};
                selection-background-color: {palette['primary']};
                selection-color: {palette['selected_text']};
            }}
            QCalendarWidget QTableView::item:enabled {{
                background-color: {palette['time_board']};
            }}
            QCalendarWidget QTableView::item:selected {{
                color: {palette['selected_text']};
                background-color: {palette['primary']};
            }}
            QCalendarWidget QToolButton {{
                color: {palette['text']};
                background-color: {palette['time_board']};
            }}
            """
        )
        weekend_format = QTextCharFormat()
        weekend_format.setForeground(QColor(palette["weekend"]))
        calendar.setWeekdayTextFormat(Qt.DayOfWeek.Saturday, weekend_format)
        calendar.setWeekdayTextFormat(Qt.DayOfWeek.Sunday, weekend_format)
        calendar.currentPageChanged.connect(
            lambda year, month: self._style_weekend_dates(
                calendar, year, month, palette["weekend"]
            )
        )
        self._style_weekend_dates(
            calendar,
            calendar.yearShown(),
            calendar.monthShown(),
            palette["weekend"],
        )
        form.addRow(text("deadline_label", language), self.deadline_input)
        self.schedule_mode_input = PaletteComboBox(palette)
        self.schedule_mode_input.addItem(text("end_of_day", language), "end_of_day")
        self.schedule_mode_input.addItem(text("specific_time", language), "specific")
        form.addRow(text("deadline_mode", language), self.schedule_mode_input)
        self.schedule_time_input = QTimeEdit(QTime(23, 59, 59))
        self.schedule_time_input.setDisplayFormat("HH:mm:ss")
        form.addRow(text("deadline_time", language), self.schedule_time_input)

        weekdays = (
            ("weekday_monday", "weekday_tuesday", "weekday_wednesday",
             "weekday_thursday", "weekday_friday", "weekday_saturday",
             "weekday_sunday")
        )
        self.weekday_input = PaletteComboBox(palette)
        for weekday, key in enumerate(weekdays):
            self.weekday_input.addItem(text(key, language), weekday)
        form.addRow(text("weekday", language), self.weekday_input)
        self.month_day_input = QSpinBox()
        self.month_day_input.setRange(1, 31)
        self.month_day_input.setValue(1)
        form.addRow(text("month_day", language), self.month_day_input)
        self.year_date_widget = QWidget()
        year_date_layout = QHBoxLayout(self.year_date_widget)
        year_date_layout.setContentsMargins(0, 0, 0, 0)
        self.year_month_input = PaletteComboBox(palette)
        for month in range(1, 13):
            self.year_month_input.addItem(
                text(f"month_{month}", language), month
            )
        self.year_day_input = QSpinBox()
        self.year_day_input.setRange(1, 31)
        self.year_day_input.setValue(1)
        year_date_layout.addWidget(self.year_month_input)
        year_date_layout.addWidget(self.year_day_input)
        form.addRow(text("year_date", language), self.year_date_widget)
        self._schedule_rows = {
            key: (widget, form.labelForField(widget))
            for key, widget in {
                "deadline": self.deadline_input,
                "mode": self.schedule_mode_input,
                "time": self.schedule_time_input,
                "weekday": self.weekday_input,
                "month": self.month_day_input,
                "year": self.year_date_widget,
            }.items()
        }
        self.task_type_input.currentIndexChanged.connect(self._update_type_fields)
        self.schedule_mode_input.currentIndexChanged.connect(
            self._update_schedule_time
        )

        self.note_input = QTextEdit()
        self.note_input.setPlaceholderText(text("note_optional", language))
        self.note_input.setMinimumHeight(100)
        form.addRow(text("note", language), self.note_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(
            text("save", language)
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            text("cancel", language)
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        if task is not None:
            self.name_input.setText(DataBase._task_name(task))
            task_type = task.get("task_type", "type_1")
            self.task_type_input.setCurrentIndex(
                max(0, self.task_type_input.findData(task_type))
            )
            info = task["info"]
            for score, value in zip(self.score_inputs, info[:10]):
                score.setValue(float(value))
            deadline = datetime.strptime(info[10], DataBase.DATE_FORMAT)
            self.deadline_input.setDateTime(
                QDateTime.fromString(
                    deadline.strftime(DataBase.DATE_FORMAT),
                    "dd/MM/yyyy HH:mm:ss",
                )
            )
            schedule = task.get("schedule", {})
            self.weekday_input.setCurrentIndex(
                self.weekday_input.findData(schedule.get("weekday", 0))
            )
            self.month_day_input.setValue(schedule.get("day", 1))
            self.year_month_input.setCurrentIndex(
                self.year_month_input.findData(schedule.get("month", 1))
            )
            self.year_day_input.setValue(schedule.get("day", 1))
            self.schedule_mode_input.setCurrentIndex(
                max(
                    0,
                    self.schedule_mode_input.findData(
                        schedule.get("deadline_mode", "end_of_day")
                    ),
                )
            )
            parsed_time = datetime.strptime(
                schedule.get("deadline_time", "23:59:59"), DataBase.TIME_FORMAT
            ).time()
            self.schedule_time_input.setTime(
                QTime(parsed_time.hour, parsed_time.minute, parsed_time.second)
            )
            self.note_input.setPlainText(str(task.get("note", "")))
        self._update_type_fields()

    def get_task_values(
        self,
    ) -> tuple[list[Any], str, str, str, dict[str, Any] | None]:
        scores = [score.value() for score in self.score_inputs]
        task_type = str(self.task_type_input.currentData())
        schedule = None
        if task_type == "type_1":
            deadline = self.deadline_input.dateTime().toString(
                "dd/MM/yyyy HH:mm:ss"
            )
        else:
            deadline_time = (
                self.schedule_time_input.time().toString("HH:mm:ss")
                if self.schedule_mode_input.currentData() == "specific"
                else "23:59:59"
            )
            schedule = {
                "deadline_mode": self.schedule_mode_input.currentData(),
                "deadline_time": deadline_time,
            }
            if task_type == "type_3":
                schedule["weekday"] = self.weekday_input.currentData()
            elif task_type == "type_4":
                schedule["day"] = self.month_day_input.value()
            elif task_type == "type_5":
                schedule.update(
                    month=self.year_month_input.currentData(),
                    day=self.year_day_input.value(),
                )
            deadline = datetime.combine(
                datetime.now().date() + timedelta(days=1),
                datetime.strptime(deadline_time, DataBase.TIME_FORMAT).time(),
            ).strftime(DataBase.DATE_FORMAT)
        return (
            scores + [deadline],
            self.name_input.text().strip(),
            self.note_input.toPlainText(),
            task_type,
            schedule,
        )

    def _update_type_fields(self) -> None:
        task_type = self.task_type_input.currentData()
        visibility = {
            "deadline": task_type == "type_1",
            "mode": task_type != "type_1",
            "time": (
                task_type != "type_1"
                and self.schedule_mode_input.currentData() == "specific"
            ),
            "weekday": task_type == "type_3",
            "month": task_type == "type_4",
            "year": task_type == "type_5",
        }
        for key, visible in visibility.items():
            widget, label = self._schedule_rows[key]
            widget.setVisible(visible)
            if label is not None:
                label.setVisible(visible)

    def _update_schedule_time(self) -> None:
        if hasattr(self, "_schedule_rows"):
            self._update_type_fields()

    @staticmethod
    def _style_weekend_dates(
        calendar: Any, year: int, month: int, weekend_color: str
    ) -> None:
        first_day = QDate(year, month, 1)
        first_visible = first_day.addDays(1 - first_day.dayOfWeek())
        weekend_format = QTextCharFormat()
        weekend_format.setForeground(QColor(weekend_color))
        for offset in range(42):
            date = first_visible.addDays(offset)
            if date.dayOfWeek() in (6, 7):
                calendar.setDateTextFormat(date, weekend_format)


class SettingsDialog(QDialog):
    def __init__(self, settings: Settings, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self.language = str(settings.Language)
        self.setWindowTitle(text("settings", self.language))
        self.setMinimumWidth(420)

        self.setWindowIcon(QIcon(str(ICON_FILE)))
        layout = QVBoxLayout(self)
        form = QFormLayout()
        palette = colors(str(settings.mode))
        self.controls: dict[str, QCheckBox | QSpinBox | QComboBox] = {}
        labels = {
            "auto_start": "auto_start",
            "TimeAlertBeforeDeadline": "deadline_alert",
            "AutoPrintList": "auto_print",
            "RemindTask": "reminder_interval",
            "AutoRefestWeight": "weight_interval",
            "mode": "mode",
            "Language": "language",
            "Toast detail": "toast_detail",
            "Just Show Only TrayIon": "show_only_tray",
        }
        for name, label_key in labels.items():
            value = getattr(settings, name)
            if isinstance(value, bool):
                control: QCheckBox | QSpinBox | QComboBox = QCheckBox()
                control.setChecked(value)
            elif isinstance(value, str):
                control = PaletteComboBox(palette)
                options = Settings.OPTIONS[name]
                control.addItems(
                    [
                        text(option.casefold(), self.language)
                        if name == "Toast detail"
                        else option
                        for option in options
                    ]
                )
                control.setCurrentIndex(options.index(value))
            else:
                control = QSpinBox()
                control.setRange(0, 1_000_000)
                control.setValue(value)
            self.controls[name] = control
            form.addRow(text(label_key, self.language), control)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText(
            text("save", self.language)
        )
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText(
            text("cancel", self.language)
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _save(self) -> None:
        updates: dict[str, bool | int | str] = {}
        for name, control in self.controls.items():
            if isinstance(control, QCheckBox):
                updates[name] = control.isChecked()
            elif isinstance(control, QComboBox):
                value = control.currentText()
                if name == "Toast detail":
                    value = (
                        "Detailed"
                        if control.currentIndex() == 1
                        else "Simple"
                    )
                updates[name] = value
            else:
                updates[name] = control.value()
        try:
            self.settings.set_values(**updates)
        except (OSError, TypeError, ValueError) as exc:
            logger.exception("Could not save application settings")
            QMessageBox.critical(
                self,
                text("settings_error_title", self.language),
                text("settings_error", self.language, error=exc),
            )
            return
        self.accept()


class MainWindow(QMainWindow):
    def __init__(
        self,
        database: DataBase,
        weights_name: list[str],
        settings: Settings,
    ) -> None:
        super().__init__()
        self.database = database
        self.weights_name = weights_name
        self.settings = settings
        self._tasks: dict[str, dict[str, Any]] = {}
        self.setWindowTitle(f"TasksHere {METADATA["version"]}")
        self.resize(1100, 720)
        self.setMinimumSize(800, 540)

        self.setWindowIcon(QIcon(str(ICON_FILE)))

        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(16)

        header = QHBoxLayout()
        title_block = QVBoxLayout()
        title = QLabel(f"TasksHere {METADATA["version"]}")
        title.setStyleSheet("font-size: 25px; font-weight: 700;")

        self.credit_label = QLabel()
        self.credit_label.setStyleSheet("""
            QLabel {
                color: #7d7c7c;  
                font-size: 13px;   
                font-family: "Segoe UI", "Arial", sans-serif;
            }
        """)

        self.subtitle_label = QLabel()
        title_block.addWidget(title)
        title_block.setSpacing(3) 
        title_block.addWidget(self.credit_label)
        title_block.addSpacing(20)
        title_block.addWidget(self.subtitle_label)
        header.addLayout(title_block)
        header.addStretch()
        self.settings_button = QPushButton()
        self.settings_button.clicked.connect(self._open_settings)
        header.addWidget(self.settings_button)
        self.refresh_button = QPushButton()
        self.refresh_button.clicked.connect(self._refresh_weights)
        header.addWidget(self.refresh_button)
        self.add_button = QPushButton()
        self.add_button.setObjectName("primary")
        self.add_button.clicked.connect(self._add_task)
        header.addWidget(self.add_button)
        root.addLayout(header)

        summary = QHBoxLayout()
        self.count_label = QLabel()
        self.priority_label = QLabel()
        summary.addWidget(self.count_label)
        summary.addWidget(self.priority_label, 1)
        root.addLayout(summary)

        self.search_input = QLineEdit()
        self.search_input.textChanged.connect(self._apply_filter)
        root.addWidget(self.search_input)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        task_panel = QWidget()
        task_layout = QVBoxLayout(task_panel)
        task_layout.setContentsMargins(0, 0, 0, 0)
        task_layout.setSpacing(10)

        self.active_title = QLabel()
        self.active_title.setStyleSheet("font-size:15px; font-weight:700;")
        self.task_type_filter = self._create_type_filter()
        self.task_type_filter.currentIndexChanged.connect(
            self._type_filter_changed
        )
        active_header = QHBoxLayout()
        active_header.addWidget(self.active_title)
        active_header.addStretch()
        active_header.addWidget(self.task_type_filter)
        self.task_table = QTableWidget(0, 4)
        self.task_table.setHorizontalHeaderLabels(["", "", "", ""])
        self._configure_task_table(self.task_table)
        self.task_table.itemSelectionChanged.connect(
            self._active_selection_changed
        )
        self.task_table.cellDoubleClicked.connect(self._edit_task)
        active_panel = QWidget()
        active_layout = QVBoxLayout(active_panel)
        active_layout.setContentsMargins(0, 0, 0, 0)
        active_layout.addLayout(active_header)
        active_layout.addWidget(self.task_table)

        timeout_header = QHBoxLayout()
        self.timeout_title = QLabel()
        self.timeout_title.setStyleSheet("font-size:15px; font-weight:700;")
        timeout_header.addWidget(self.timeout_title)
        timeout_header.addStretch()
        self.timeout_type_filter = self._create_type_filter()
        self.timeout_type_filter.currentIndexChanged.connect(
            self._type_filter_changed
        )
        timeout_header.addWidget(self.timeout_type_filter)
        self.clear_button = QPushButton()
        self.clear_button.clicked.connect(self._clear_timed_out_tasks)
        timeout_header.addWidget(self.clear_button)

        self.timeout_table = QTableWidget(0, 4)
        self.timeout_table.setHorizontalHeaderLabels(["", "", "", ""])
        self._configure_task_table(self.timeout_table)
        self.timeout_table.itemSelectionChanged.connect(
            self._timeout_selection_changed
        )
        self.timeout_table.cellDoubleClicked.connect(self._edit_task)
        timeout_panel = QWidget()
        timeout_layout = QVBoxLayout(timeout_panel)
        timeout_layout.setContentsMargins(0, 0, 0, 0)
        timeout_layout.addLayout(timeout_header)
        timeout_layout.addWidget(self.timeout_table)

        self.task_tables: dict[str, QTableWidget] = {
            "active": self.task_table,
            "timed_out": self.timeout_table,
        }
        lists_splitter = QSplitter(Qt.Orientation.Vertical)
        lists_splitter.addWidget(active_panel)
        lists_splitter.addWidget(timeout_panel)
        lists_splitter.setSizes([350, 250])
        task_layout.addWidget(lists_splitter, 1)
        splitter.addWidget(task_panel)


        detail = QFrame()
        detail.setObjectName("card")
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(18, 18, 18, 18)
        self.detail_title = QLabel()
        self.detail_title.setStyleSheet("font-size:16px; font-weight:700;")
        detail_layout.addWidget(self.detail_title)
        self.detail_name = QLabel()
        self.detail_name.setWordWrap(True)
        self.detail_name.setStyleSheet(
            "font-size:18px; font-weight:700; margin-top:8px;"
        )
        detail_layout.addWidget(self.detail_name)
        self.detail_meta = QLabel("")
        self.detail_meta.setWordWrap(True)
        detail_layout.addWidget(self.detail_meta)
        self.scores_label = QLabel()
        detail_layout.addWidget(self.scores_label)
        self.score_list = QListWidget()
        self.score_list.setMaximumHeight(210)
        detail_layout.addWidget(self.score_list)
        self.note_label = QLabel()
        detail_layout.addWidget(self.note_label)
        self.detail_note = QTextEdit()
        self.detail_note.setReadOnly(True)
        self.detail_note.setMinimumHeight(110)
        detail_layout.addWidget(self.detail_note, 1)

        actions = QHBoxLayout()
        self.edit_button = QPushButton()
        self.edit_button.clicked.connect(self._edit_task)
        self.edit_button.setEnabled(False)
        self.delete_button = QPushButton()
        self.delete_button.clicked.connect(self._remove_task)
        self.delete_button.setEnabled(False)
        actions.addWidget(self.edit_button)
        actions.addWidget(self.delete_button)
        detail_layout.addLayout(actions)
        splitter.addWidget(detail)
        splitter.setSizes([700, 340])
        root.addWidget(splitter, 1)

        self.setCentralWidget(central)
        self._apply_theme()
        self._apply_language()
        self._refresh_tasks()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setInterval(30_000)
        self.refresh_timer.timeout.connect(self._refresh_tasks)
        self.refresh_timer.start()

    def _apply_theme(self) -> None:
        palette = colors(str(self.settings.mode))
        self.setStyleSheet(
            f"""
            QMainWindow, QDialog {{ background: {palette['window']}; }}
            QWidget {{ color: {palette['text']}; font-size: 13px; }}

            /* Sửa lại viền card và bảng sang màu palette để giảm tương phản gắt */
            QFrame#card, QTableWidget, QTextEdit, QLineEdit, QSpinBox,
            QDoubleSpinBox, QDateTimeEdit, QListWidget, QComboBox {{
                background: {palette['surface']};
                border: 1px solid {palette['border']};
                border-radius: 8px;
            }}
            QFrame#card, QTableWidget {{
                border: 1px solid {palette['border']};
            }}
            QLineEdit, QSpinBox, QDoubleSpinBox, QDateTimeEdit, QComboBox {{
                padding: 7px;
            }}
            QPushButton {{
                background: {palette['surface']};
                border: 1px solid {palette['border']};
                border-radius: 7px; padding: 8px 14px;
            }}
            QPushButton:hover {{ background: {palette['hover']}; }}
            QPushButton#primary {{
                background: {palette['primary']}; color: white; border: none;
                font-weight: 600;
            }}
            QPushButton#primary:hover {{
                background: {palette['primary_hover']};
            }}
            QHeaderView::section {{
                background: {palette['header']}; border: none; padding: 10px;
                color: {palette['muted']}; font-weight: 600;
            }}
            QTableWidget {{ gridline-color: {palette['grid']}; }}
            QTableWidget::item {{
                padding: 7px; border-bottom: 1px solid {palette['grid']};
            }}
            QTableWidget::item:selected {{
                background: {palette['selection']}; color: {palette['text']};
            }}
            QScrollBar:vertical, QScrollBar:horizontal {{
                background: {palette['window']};
                border: 1px solid {palette['border']};
                border-radius: 5px;
            }}
            QScrollBar:vertical {{ width: 12px; margin: 0; }}
            QScrollBar:horizontal {{ height: 12px; margin: 0; }}
            QScrollBar::handle:vertical, QScrollBar::handle:horizontal {{
                background: {palette["scroller"]}; border-radius: 4px; min-height: 24px;
                min-width: 24px;
            }}
            QScrollBar::add-line, QScrollBar::sub-line {{
                width: 0; height: 0;
            }}
            QScrollBar::add-page, QScrollBar::sub-page {{
                background: {palette['window']};
            }}

            QComboBox::drop-down {{
                width: 24px;
                background: {palette['surface']};
                border-left: 1px solid {palette['border']};
            }}
            QComboBox {{
                padding: 7px;
            }}
            QComboBox QAbstractItemView {{
                background: {palette['surface']};
                color: {palette['text']};
                border: 1px solid {palette['border']};
                selection-background-color: {palette['selection']};
                selection-color: {palette['text']};
                outline: 0;
                padding: 0;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 6px 10px;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background: {palette['selection']};
                color: {palette['text']};
            }}
            """
        )
        for combo in self.findChildren(PaletteComboBox):
            combo.set_popup_palette(palette)

    def _apply_language(self) -> None:
        language = str(self.settings.Language)
        self.subtitle_label.setText(text("window_subtitle", language))
        self.active_title.setText(text("active_tasks", language))
        for type_filter in (
            self.task_type_filter,
            self.timeout_type_filter,
        ):
            type_filter.setItemText(0, text("all_types", language))
            for index, task_type in enumerate(
                ("type_2", "type_3", "type_4", "type_5"), start=1
            ):
                type_filter.setItemText(
                    index,
                    text(TASK_TYPE_FILTER_TEXT_KEYS[task_type], language),
                )
        self.settings_button.setText(text("settings", language))
        self.refresh_button.setText(text("refresh", language))
        self.add_button.setText(text("add_task", language))
        self.search_input.setPlaceholderText(text("search", language))
        self.detail_title.setText(text("task_details", language))
        self.scores_label.setText(text("scores", language))
        self.note_label.setText(text("note", language))
        self.edit_button.setText(text("edit", language))
        self.delete_button.setText(text("delete", language))
        self.credit_label.setText(text("credit", language) + METADATA["credit"])
        self.timeout_title.setText(
            text(
                "timeout_count",
                language,
                count=self.timeout_table.rowCount(),
            )
        )
        self.clear_button.setText(text("clear_deadline_timeouts", language))
        if not self.detail_name.text() or self.detail_name.text() in {
            text("select_task", "Vie"),
            text("select_task", "Eng"),
        }:
            self.detail_name.setText(text("select_task", language))
        for table in self.task_tables.values():
            table.setHorizontalHeaderLabels(
                [
                    text("task_name", language),
                    text("list_type", language),
                    text("priority", language),
                    text("deadline", language),
                ]
            )
        self._update_summary_labels(0, None)

    def _configure_task_table(self, table: QTableWidget) -> None:
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        table.setColumnWidth(1, 120)
        table.setColumnWidth(2, 100)
        table.setColumnWidth(3, 150)

    def _create_type_filter(self) -> QComboBox:
        type_filter = PaletteComboBox(colors(str(self.settings.mode)))
        type_filter.addItem(text("all_types", str(self.settings.Language)), "all")
        for task_type in ("type_2", "type_3", "type_4", "type_5"):
            type_filter.addItem(
                text(
                    TASK_TYPE_FILTER_TEXT_KEYS[task_type],
                    str(self.settings.Language),
                ),
                task_type,
            )
        return type_filter

    def _update_summary_labels(
        self, task_count: int, top_task: dict[str, Any] | None
    ) -> None:
        language = str(self.settings.Language)
        self.count_label.setText(
            text("task_count", language, count=task_count)
        )
        if top_task is None:
            self.priority_label.setText(text("no_priority", language))
        else:
            self.priority_label.setText(
                text(
                    "top_priority",
                    language,
                    name=DataBase._task_name(top_task),
                    weight=top_task["weight"],
                )
            )

    def _selected_task(self) -> dict[str, Any] | None:
        for table in self.task_tables.values():
            row = table.currentRow()
            if row >= 0:
                item = table.item(row, 0)
                if item is not None:
                    name = item.data(Qt.ItemDataRole.UserRole)
                    task = self._tasks.get(str(name).casefold())
                    if task is not None:
                        return task
        return None

    def _refresh_tasks(self, selected_name: str | None = None) -> None:
        try:
            tasks = self.database.get_tasks()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.exception("Could not load tasks for the GUI")
            QMessageBox.critical(
                self,
                text("load_error_title", str(self.settings.Language)),
                text("load_error", str(self.settings.Language), error=exc),
            )
            return

        try:
            self._tasks = {
                DataBase._task_name(task).casefold(): task for task in tasks
            }
            now = datetime.now()
            active_tasks = [
                task for task in tasks
                if not self.database.is_timed_out(task, now)
            ]
            timed_out_tasks = [
                task for task in tasks
                if self.database.is_timed_out(task, now)
            ]
        except (ValueError, KeyError, TypeError) as exc:
            logger.exception("Could not classify tasks by deadline")
            QMessageBox.critical(
                self,
                text("load_error_title", str(self.settings.Language)),
                text("load_error", str(self.settings.Language), error=exc),
            )
            return
        self._update_summary_labels(
            len(active_tasks), active_tasks[0] if active_tasks else None
        )
        for table in self.task_tables.values():
            table.blockSignals(True)
            table.clearContents()
            table.setRowCount(0)
        self._populate_table(self.task_table, active_tasks)
        self._populate_table(self.timeout_table, timed_out_tasks)
        for table in self.task_tables.values():
            table.blockSignals(False)
        clearable_count = sum(
            task.get("task_type", "type_1") == "type_1"
            for task in timed_out_tasks
        )
        self.clear_button.setEnabled(clearable_count > 0)
        self.timeout_title.setText(
            text(
                "timeout_count",
                str(self.settings.Language),
                count=len(timed_out_tasks),
            )
        )

        if selected_name:
            target = selected_name.casefold()
            self.task_type_filter.setCurrentIndex(0)
            self.timeout_type_filter.setCurrentIndex(0)
            if not self._select_task(self.task_table, target):
                self._select_task(self.timeout_table, target)
        elif self.task_table.rowCount():
            self.task_table.selectRow(0)
        elif self.timeout_table.rowCount():
            self.timeout_table.selectRow(0)
        self._apply_filter(self.search_input.text())
        self._show_selection()

    def _populate_table(
        self,
        table: QTableWidget,
        tasks: list[dict[str, Any]],
    ) -> None:
        for task in tasks:
            row = table.rowCount()
            table.insertRow(row)
            name = DataBase._task_name(task)
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.ItemDataRole.UserRole, name)
            table.setItem(row, 0, name_item)
            task_type = task.get("task_type", "type_1")
            table.setItem(
                row,
                1,
                QTableWidgetItem(
                    text(
                        TASK_TYPE_TEXT_KEYS[task_type],
                        str(self.settings.Language),
                    )
                ),
            )
            table.setItem(row, 2, QTableWidgetItem(f"{task['weight']:.2f}"))
            table.setItem(row, 3, QTableWidgetItem(str(task["info"][10])))

    @staticmethod
    def _select_task(table: QTableWidget, target: str) -> bool:
        for row in range(table.rowCount()):
            item = table.item(row, 0)
            if (
                item
                and str(item.data(Qt.ItemDataRole.UserRole)).casefold()
                == target
            ):
                table.selectRow(row)
                return True
        return False

    def _apply_filter(self, query: str) -> None:
        needle = query.strip().casefold()
        for table, type_filter in (
            (self.task_table, self.task_type_filter),
            (self.timeout_table, self.timeout_type_filter),
        ):
            selected_type = type_filter.currentData()
            for row in range(table.rowCount()):
                name_item = table.item(row, 0)
                task = (
                    self._tasks.get(
                        str(name_item.data(Qt.ItemDataRole.UserRole)).casefold()
                    )
                    if name_item
                    else None
                )
                searchable = (
                    " ".join(
                        (
                            DataBase._task_name(task),
                            str(task.get("note", "")),
                            str(task["info"][10]),
                        )
                    ).casefold()
                    if task
                    else ""
                )
                matches_type = (
                    selected_type == "all"
                    or (
                        task is not None
                        and task.get("task_type", "type_1") == selected_type
                    )
                )
                table.setRowHidden(
                    row, needle not in searchable or not matches_type
                )

    def _type_filter_changed(self, _index: int) -> None:
        self._apply_filter(self.search_input.text())

    def _show_selection(self) -> None:
        task = self._selected_task()
        has_task = task is not None
        self.edit_button.setEnabled(has_task)
        self.delete_button.setEnabled(has_task)
        self.score_list.clear()
        if task is None:
            self.detail_name.setText(
                text("select_task", str(self.settings.Language))
            )
            self.detail_meta.clear()
            self.detail_note.clear()
            return

        name = DataBase._task_name(task)
        info = task["info"]
        self.detail_name.setText(name)
        language = str(self.settings.Language)
        task_type = task.get("task_type", "type_1")
        details = [
            f"{text('task_type', language)}: "
            f"{text(TASK_TYPE_TEXT_KEYS[task_type], language)}",
            f"{text('priority', language)}: {task['weight']:.2f}",
            f"{text('deadline', language)}: {info[10]}",
        ]
        if task_type != "type_1":
            schedule = task["schedule"]
            time_label = (
                text("end_of_day", language)
                if schedule["deadline_mode"] == "end_of_day"
                else schedule["deadline_time"]
            )
            if task_type == "type_2":
                key = "schedule_daily"
                values = {"time": time_label}
            elif task_type == "type_3":
                key = "schedule_weekly"
                weekday_key = (
                    "weekday_monday",
                    "weekday_tuesday",
                    "weekday_wednesday",
                    "weekday_thursday",
                    "weekday_friday",
                    "weekday_saturday",
                    "weekday_sunday",
                )[schedule["weekday"]]
                values = {
                    "weekday": text(weekday_key, language),
                    "time": time_label,
                }
            elif task_type == "type_4":
                key = "schedule_monthly"
                values = {"day": schedule["day"], "time": time_label}
            else:
                key = "schedule_yearly"
                values = {
                    "month": text(f"month_{schedule['month']}", language),
                    "day": schedule["day"],
                    "time": time_label,
                }
            details.append(text(key, language, **values))
        details.append(
            f"{'Tạo lúc' if language == 'Vie' else 'Created'}: "
            f"{task.get('created_at', '—')}"
        )
        self.detail_meta.setText(
            "\n".join(details)
        )
        self.detail_note.setPlainText(str(task.get("note", "")))
        for label, value in zip(self.weights_name[:10], info[:10]):
            self.score_list.addItem(
                QListWidgetItem(
                    f"{score_label(label, language)}: {float(value):g}/5"
                )
            )

    def _active_selection_changed(self) -> None:
        self._clear_other_selections(self.sender())

    def _timeout_selection_changed(self) -> None:
        self._clear_other_selections(self.timeout_table)

    def _clear_other_selections(self, selected: Any) -> None:
        if not isinstance(selected, QTableWidget) or selected.currentRow() < 0:
            self._show_selection()
            return
        for table in self.task_tables.values():
            if table is not selected and table.currentRow() >= 0:
                table.blockSignals(True)
                table.clearSelection()
                table.blockSignals(False)
        self._show_selection()

    def _refresh_weights(self) -> None:
        try:
            self.database.refresh_weights()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.exception("Could not refresh task priorities")
            QMessageBox.critical(
                self,
                text("load_error_title", str(self.settings.Language)),
                text("load_error", str(self.settings.Language), error=exc),
            )
            return
        self._refresh_tasks()

    def _clear_timed_out_tasks(self) -> None:
        count = sum(
            task.get("task_type", "type_1") == "type_1"
            and self.database.is_timed_out(task)
            for task in self._tasks.values()
        )
        if not count:
            return
        language = str(self.settings.Language)
        answer = QMessageBox.question(
            self,
            text("clear_deadline_timeouts", language),
            text("confirm_clear", language, count=count),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.database.clear_timed_out_tasks()
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.exception("Could not clear timed-out tasks")
            QMessageBox.critical(
                self,
                text("clear_error_title", language),
                text("remove_error", language, error=exc),
            )
            return
        self._refresh_tasks()

    def show_task(self, task_name: str) -> None:
        self.search_input.clear()
        self._refresh_tasks(task_name)
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _add_task(self) -> None:
        language = str(self.settings.Language)
        dialog = TaskDialog(
            self.weights_name,
            language=language,
            mode=str(self.settings.mode),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        info, name, note, task_type, schedule = dialog.get_task_values()
        try:
            self.database.new_task(info, name, note, task_type, schedule)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.exception("Could not create task %r", name)
            QMessageBox.warning(
                self,
                text("create_error_title", language),
                text("invalid_task", language, error=exc),
            )
            return
        self._refresh_tasks(name)

    def _edit_task(self) -> None:
        task = self._selected_task()
        if task is None:
            return
        old_name = DataBase._task_name(task)
        language = str(self.settings.Language)
        dialog = TaskDialog(
            self.weights_name,
            task=task,
            language=language,
            mode=str(self.settings.mode),
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        info, name, note, task_type, schedule = dialog.get_task_values()
        try:
            self.database.update_task(
                old_name,
                info,
                note,
                new_name=name,
                task_type=task_type,
                schedule=schedule,
            )
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.exception("Could not update task %r", old_name)
            QMessageBox.warning(
                self,
                text("update_error_title", language),
                text("invalid_task", language, error=exc),
            )
            return
        self._refresh_tasks(name)

    def _remove_task(self) -> None:
        task = self._selected_task()
        if task is None:
            return
        name = DataBase._task_name(task)
        language = str(self.settings.Language)
        answer = QMessageBox.question(
            self,
            text("confirm_delete_title", language),
            text("confirm_delete", language, name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.database.remove_task(name)
        except (OSError, ValueError, KeyError, TypeError) as exc:
            logger.exception("Could not delete task %r", name)
            QMessageBox.critical(
                self,
                text("remove_error_title", language),
                text("remove_error", language, error=exc),
            )
            return
        self._refresh_tasks()

    def _open_settings(self) -> None:
        previous_auto_start = self.settings.auto_start
        dialog = SettingsDialog(self.settings, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self._apply_theme()
        self._apply_language()
        if (
            isinstance(previous_auto_start, bool)
            and previous_auto_start != self.settings.auto_start
        ):
            if os.name == "nt":
                try:
                    from Background import (
                        _auto_start_command,
                        _auto_start_of,
                        _auto_start_on,
                    )

                    if self.settings.auto_start:
                        _auto_start_on(
                            _auto_start_command("main_gui.py")
                        )
                    else:
                        _auto_start_of()
                except OSError as exc:
                    logger.exception("Could not update Windows auto-start")
                    try:
                        self.settings.set_auto_start(previous_auto_start)
                    except OSError as rollback_error:
                        logger.exception(
                            "Could not roll back the auto-start setting"
                        )
                        QMessageBox.critical(
                            self,
                            text(
                                "auto_start_error_title",
                                str(self.settings.Language),
                            ),
                            text(
                                "settings_error",
                                str(self.settings.Language),
                                error=rollback_error,
                            ),
                        )
                        return
                    QMessageBox.warning(
                        self,
                        text(
                            "auto_start_error_title",
                            str(self.settings.Language),
                        ),
                        text(
                            "auto_start_rollback",
                            str(self.settings.Language),
                            error=exc,
                        ),
                    )
        self._refresh_tasks()

    def closeEvent(self, event: QCloseEvent) -> None:
        self.hide()
        event.ignore()
        return