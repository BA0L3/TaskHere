from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any

from config import METADATA

from PySide6.QtCore import QDate, QDateTime, Qt, QTimer
from PySide6.QtGui import QColor, QTextCharFormat, QIcon
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
    QVBoxLayout,
    QWidget,
)

from Database import DataBase
from Settings import Settings
from i18n import colors, score_label, text
from config import ICON_FILE


logger = logging.getLogger(__name__)


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
            self.note_input.setPlainText(str(task.get("note", "")))

    def get_task_values(self) -> tuple[list[Any], str, str]:
        scores = [score.value() for score in self.score_inputs]
        deadline = self.deadline_input.dateTime().toString(
            "dd/MM/yyyy HH:mm:ss"
        )
        return scores + [deadline], self.name_input.text().strip(), (
            self.note_input.toPlainText()
        )

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
                control = QComboBox()
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
        self._apply_theme()

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
        task_layout.addWidget(self.active_title)
        self.task_table = QTableWidget(0, 3)
        self.task_table.setHorizontalHeaderLabels(["", "", ""])
        self._configure_task_table(self.task_table, timed_out=False)
        self.task_table.itemSelectionChanged.connect(
            self._active_selection_changed
        )
        self.task_table.cellDoubleClicked.connect(self._edit_task)
        task_layout.addWidget(self.task_table, 3)

        timeout_header = QHBoxLayout()
        self.timeout_title = QLabel()
        self.timeout_title.setStyleSheet("font-size:15px; font-weight:700;")
        timeout_header.addWidget(self.timeout_title)
        timeout_header.addStretch()
        self.clear_button = QPushButton()
        self.clear_button.clicked.connect(self._clear_timed_out_tasks)
        timeout_header.addWidget(self.clear_button)
        task_layout.addLayout(timeout_header)

        self.timeout_table = QTableWidget(0, 2)
        self.timeout_table.setHorizontalHeaderLabels(["", ""])
        self._configure_task_table(self.timeout_table, timed_out=True)
        self.timeout_table.itemSelectionChanged.connect(
            self._timeout_selection_changed
        )
        self.timeout_table.cellDoubleClicked.connect(self._edit_task)
        task_layout.addWidget(self.timeout_table, 2)
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
            QFrame#card, QTableWidget, QTextEdit, QLineEdit, QSpinBox,
            QDoubleSpinBox, QDateTimeEdit, QListWidget, QComboBox {{
                background: {palette['surface']};
                border: 1px solid {palette['border']};
                border-radius: 8px;
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
            QTableWidget::item {{ padding: 7px; }}
            QTableWidget::item:selected {{
                background: {palette['selection']}; color: {palette['text']};
            }}
            QComboBox::drop-down {{
                background: {palette['surface']};
                border-left: 1px solid {palette['border']};
            }}
            QComboBox QAbstractItemView {{
                background: {palette['surface']};
                color: {palette['text']};
                selection-background-color: {palette['selection']};
                selection-color: {palette['text']};
                outline: 0;
            }}
            """
        )

    def _apply_language(self) -> None:
        language = str(self.settings.Language)
        self.subtitle_label.setText(text("window_subtitle", language))
        self.active_title.setText(text("active_tasks", language))
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
        self.clear_button.setText(text("clear", language))
        if not self.detail_name.text() or self.detail_name.text() in {
            text("select_task", "Vie"),
            text("select_task", "Eng"),
        }:
            self.detail_name.setText(text("select_task", language))
        self.task_table.setHorizontalHeaderLabels(
            [
                text("task_name", language),
                text("priority", language),
                text("deadline", language),
            ]
        )
        self.timeout_table.setHorizontalHeaderLabels(
            [text("task_name", language), text("deadline", language)]
        )
        self._update_summary_labels(0, None)

    def _configure_task_table(
        self, table: QTableWidget, timed_out: bool
    ) -> None:
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        if not timed_out:
            table.setColumnWidth(1, 120)

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
        for table in (self.task_table, self.timeout_table):
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
        for table in (self.task_table, self.timeout_table):
            table.blockSignals(True)
            table.clearContents()
            table.setRowCount(0)
        self._populate_table(self.task_table, active_tasks, timed_out=False)
        self._populate_table(self.timeout_table, timed_out_tasks, timed_out=True)
        self.task_table.blockSignals(False)
        self.timeout_table.blockSignals(False)
        self.timeout_title.setText(
            text(
                "timeout_count",
                str(self.settings.Language),
                count=len(timed_out_tasks),
            )
        )

        if selected_name:
            target = selected_name.casefold()
            found = self._select_task(self.task_table, target)
            if not found:
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
        timed_out: bool,
    ) -> None:
        for task in tasks:
            row = table.rowCount()
            table.insertRow(row)
            name = DataBase._task_name(task)
            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.ItemDataRole.UserRole, name)
            table.setItem(row, 0, name_item)
            if timed_out:
                table.setItem(row, 1, QTableWidgetItem(str(task["info"][10])))
            else:
                table.setItem(
                    row, 1, QTableWidgetItem(f"{task['weight']:.2f}")
                )
                table.setItem(
                    row, 2, QTableWidgetItem(str(task["info"][10]))
                )

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
        for table in (self.task_table, self.timeout_table):
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
                table.setRowHidden(row, needle not in searchable)

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
        self.detail_meta.setText(
            f"{text('priority', language)}: {task['weight']:.2f}\n"
            f"{text('deadline', language)}: {info[10]}\n"
            f"{'Tạo lúc' if language == 'Vie' else 'Created'}: "
            f"{task.get('created_at', '—')}"
        )
        self.detail_note.setPlainText(str(task.get("note", "")))
        for label, value in zip(self.weights_name[:10], info[:10]):
            self.score_list.addItem(
                QListWidgetItem(
                    f"{score_label(label, language)}: {float(value):g}/5"
                )
            )

    def _active_selection_changed(self) -> None:
        if self.task_table.currentRow() >= 0:
            self.timeout_table.clearSelection()
        self._show_selection()

    def _timeout_selection_changed(self) -> None:
        if self.timeout_table.currentRow() >= 0:
            self.task_table.clearSelection()
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
        count = self.timeout_table.rowCount()
        if not count:
            return
        language = str(self.settings.Language)
        answer = QMessageBox.question(
            self,
            text("clear", language),
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
        info, name, note = dialog.get_task_values()
        try:
            self.database.new_task(info, name, note)
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
        info, name, note = dialog.get_task_values()
        try:
            self.database.update_task(old_name, info, note, new_name=name)
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
