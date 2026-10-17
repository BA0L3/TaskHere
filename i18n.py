from typing import Literal


Language = Literal["Vie", "Eng"]
Mode = Literal["Light", "Dark"]


TEXTS: dict[str, dict[Language, str]] = {
    "window_subtitle": {
        "Vie": "Sắp xếp công việc theo mức độ ưu tiên",
        "Eng": "Prioritize and organize your tasks",
    },
    "active_tasks": {"Vie": "Tác vụ", "Eng": "Tasks"},
    "all_types": {"Vie": "Tất cả", "Eng": "All"},
    "settings": {"Vie": "Cài đặt", "Eng": "Settings"},
    "refresh": {"Vie": "Làm mới", "Eng": "Refresh"},
    "add_task": {"Vie": "+  Tạo tác vụ", "Eng": "+  Add task"},
    "task_count": {"Vie": "{count} tác vụ", "Eng": "{count} tasks"},
    "top_priority": {
        "Vie": "Ưu tiên cao nhất: {name} · {weight:.2f}",
        "Eng": "Top priority: {name} · {weight:.2f}",
    },
    "no_priority": {
        "Vie": "Ưu tiên cao nhất: —",
        "Eng": "Top priority: —",
    },
    "search": {
        "Vie": "Tìm theo tên, ghi chú hoặc deadline...",
        "Eng": "Search name, note, or deadline...",
    },
    "task_name": {"Vie": "Tên tác vụ", "Eng": "Task name"},
    "task_type": {"Vie": "Loại tác vụ", "Eng": "Task type"},
    "type_deadline": {"Vie": "Có deadline", "Eng": "Deadline task"},
    "type_daily": {"Vie": "Hằng ngày", "Eng": "Daily task"},
    "type_weekly": {"Vie": "Hằng tuần", "Eng": "Weekly task"},
    "type_monthly": {"Vie": "Hằng tháng", "Eng": "Monthly task"},
    "type_yearly": {"Vie": "Hằng năm", "Eng": "Yearly task"},
    "filter_daily": {"Vie": "Hằng ngày", "Eng": "Daily"},
    "filter_weekly": {"Vie": "Hằng tuần", "Eng": "Weekly"},
    "filter_monthly": {"Vie": "Hằng tháng", "Eng": "Monthly"},
    "filter_yearly": {"Vie": "Hằng năm", "Eng": "Yearly"},
    "deadline_mode": {"Vie": "Thời điểm hết hạn", "Eng": "Deadline timing"},
    "end_of_day": {"Vie": "Cuối ngày", "Eng": "End of day"},
    "specific_time": {"Vie": "Giờ cụ thể", "Eng": "Specific time"},
    "deadline_time": {"Vie": "Giờ deadline", "Eng": "Deadline time"},
    "weekday": {"Vie": "Thứ trong tuần", "Eng": "Day of week"},
    "month_day": {"Vie": "Ngày trong tháng", "Eng": "Day of month"},
    "year_date": {"Vie": "Ngày trong năm", "Eng": "Month and day"},
    "weekday_monday": {"Vie": "Thứ Hai", "Eng": "Monday"},
    "weekday_tuesday": {"Vie": "Thứ Ba", "Eng": "Tuesday"},
    "weekday_wednesday": {"Vie": "Thứ Tư", "Eng": "Wednesday"},
    "weekday_thursday": {"Vie": "Thứ Năm", "Eng": "Thursday"},
    "weekday_friday": {"Vie": "Thứ Sáu", "Eng": "Friday"},
    "weekday_saturday": {"Vie": "Thứ Bảy", "Eng": "Saturday"},
    "weekday_sunday": {"Vie": "Chủ Nhật", "Eng": "Sunday"},
    "month_1": {"Vie": "Tháng 1", "Eng": "January"},
    "month_2": {"Vie": "Tháng 2", "Eng": "February"},
    "month_3": {"Vie": "Tháng 3", "Eng": "March"},
    "month_4": {"Vie": "Tháng 4", "Eng": "April"},
    "month_5": {"Vie": "Tháng 5", "Eng": "May"},
    "month_6": {"Vie": "Tháng 6", "Eng": "June"},
    "month_7": {"Vie": "Tháng 7", "Eng": "July"},
    "month_8": {"Vie": "Tháng 8", "Eng": "August"},
    "month_9": {"Vie": "Tháng 9", "Eng": "September"},
    "month_10": {"Vie": "Tháng 10", "Eng": "October"},
    "month_11": {"Vie": "Tháng 11", "Eng": "November"},
    "month_12": {"Vie": "Tháng 12", "Eng": "December"},
    "list_type": {"Vie": "Loại", "Eng": "Type"},
    "schedule_daily": {
        "Vie": "Lặp mỗi ngày · hạn {time}",
        "Eng": "Repeats daily · due {time}",
    },
    "schedule_weekly": {
        "Vie": "Lặp mỗi {weekday} · hạn {time}",
        "Eng": "Repeats every {weekday} · due {time}",
    },
    "schedule_monthly": {
        "Vie": "Ngày {day} mỗi tháng · hạn {time}",
        "Eng": "Day {day} of each month · due {time}",
    },
    "schedule_yearly": {
        "Vie": "Ngày {day}/{month} mỗi năm · hạn {time}",
        "Eng": "{month}/{day} every year · due {time}",
    },
    "priority": {"Vie": "Điểm ưu tiên", "Eng": "Priority"},
    "deadline": {"Vie": "Deadline", "Eng": "Deadline"},
    "task_details": {"Vie": "Chi tiết tác vụ", "Eng": "Task details"},
    "select_task": {
        "Vie": "Chọn một tác vụ để xem chi tiết.",
        "Eng": "Select a task to see its details.",
    },
    "scores": {"Vie": "Điểm đánh giá", "Eng": "Scores"},
    "note": {"Vie": "Ghi chú", "Eng": "Note"},
    "edit": {"Vie": "Chỉnh sửa", "Eng": "Edit"},
    "delete": {"Vie": "Xóa", "Eng": "Delete"},
    "timeout_tasks": {"Vie": "Tác vụ quá hạn", "Eng": "Timed-out tasks"},
    "timeout_count": {
        "Vie": "Tác vụ quá hạn ({count})",
        "Eng": "Timed-out tasks ({count})",
    },
    "clear": {"Vie": "Xóa tất cả", "Eng": "Clear all"},
    "clear_deadline_timeouts": {
        "Vie": "Xóa task deadline quá hạn",
        "Eng": "Clear expired deadline tasks",
    },
    "task_dialog_add": {"Vie": "Tạo tác vụ", "Eng": "Add task"},
    "task_dialog_edit": {"Vie": "Chỉnh sửa tác vụ", "Eng": "Edit task"},
    "name_example": {
        "Vie": "Ví dụ: Hoàn thành báo cáo",
        "Eng": "For example: Finish the report",
    },
    "deadline_label": {"Vie": "Hạn hoàn thành", "Eng": "Deadline"},
    "note_optional": {
        "Vie": "Ghi chú cho tác vụ (không bắt buộc)",
        "Eng": "Optional task notes",
    },
    "save": {"Vie": "Lưu", "Eng": "Save"},
    "cancel": {"Vie": "Hủy", "Eng": "Cancel"},
    "auto_start": {
        "Vie": "Khởi động cùng Windows",
        "Eng": "Start with Windows",
    },
    "deadline_alert": {
        "Vie": "Cảnh báo trước deadline (phút)",
        "Eng": "Deadline alert lead time (minutes)",
    },
    "auto_print": {
        "Vie": "Tự hiển thị danh sách tác vụ khi mở",
        "Eng": "Show task list on startup",
    },
    "reminder_interval": {
        "Vie": "Nhắc tác vụ định kỳ (phút, 0 để tắt)",
        "Eng": "Reminder interval (minutes, 0 disables)",
    },
    "weight_interval": {
        "Vie": "Tính lại điểm định kỳ (phút, 0 để tắt)",
        "Eng": "Recalculate priority (minutes, 0 disables)",
    },
    "mode": {"Vie": "Giao diện", "Eng": "Appearance"},
    "language": {"Vie": "Ngôn ngữ", "Eng": "Language"},
    "toast_detail": {
        "Vie": "Mức chi tiết thông báo",
        "Eng": "Toast detail",
    },
    "credit": {"Vie": "Được tạo ra & phát triển bởi :", "Eng": "Created & Developed by: "},
    "show_only_tray": {
        "Vie": "Chỉ hiển thị biểu tượng khay hệ thống khi khởi động",
        "Eng": "Show only the system tray icon on startup",
    },
    "simple": {"Vie": "Đơn giản", "Eng": "Simple"},
    "detailed": {"Vie": "Chi tiết (có nút thao tác)", "Eng": "Detailed (actions)"},
    "timed_out_due": {
        "Vie": "Quá hạn: {deadline}",
        "Eng": "Expired: {deadline}",
    },
    "confirm_clear": {
        "Vie": "Xóa vĩnh viễn {count} task deadline quá hạn? Task định kỳ được giữ lại.",
        "Eng": "Permanently delete {count} expired deadline task(s)? Recurring tasks are kept.",
    },
    "confirm_delete_title": {"Vie": "Xác nhận xóa", "Eng": "Confirm deletion"},
    "confirm_delete": {
        "Vie": "Bạn có chắc muốn xóa tác vụ “{name}” không?",
        "Eng": "Are you sure you want to delete “{name}”?",
    },
    "load_error_title": {
        "Vie": "Không thể tải tác vụ",
        "Eng": "Could not load tasks",
    },
    "load_error": {
        "Vie": "Đã xảy ra lỗi khi đọc danh sách tác vụ:\n{error}",
        "Eng": "An error occurred while loading tasks:\n{error}",
    },
    "create_error_title": {
        "Vie": "Không thể tạo tác vụ",
        "Eng": "Could not create task",
    },
    "invalid_task": {
        "Vie": "Vui lòng kiểm tra thông tin tác vụ:\n{error}",
        "Eng": "Please check the task details:\n{error}",
    },
    "update_error_title": {
        "Vie": "Không thể cập nhật tác vụ",
        "Eng": "Could not update task",
    },
    "remove_error_title": {
        "Vie": "Không thể xóa tác vụ",
        "Eng": "Could not delete task",
    },
    "remove_error": {
        "Vie": "Đã xảy ra lỗi khi xóa tác vụ:\n{error}",
        "Eng": "An error occurred while deleting the task:\n{error}",
    },
    "clear_error_title": {
        "Vie": "Không thể xóa tác vụ quá hạn",
        "Eng": "Could not clear timed-out tasks",
    },
    "settings_error_title": {
        "Vie": "Không thể lưu cài đặt",
        "Eng": "Could not save settings",
    },
    "settings_error": {
        "Vie": "Đã xảy ra lỗi khi lưu cài đặt:\n{error}",
        "Eng": "An error occurred while saving settings:\n{error}",
    },
    "auto_start_error_title": {
        "Vie": "Không thể đồng bộ cài đặt",
        "Eng": "Could not sync settings",
    },
    "auto_start_rollback": {
        "Vie": "Đã khôi phục cài đặt trước đó vì Windows không thể cập nhật auto-start:\n{error}",
        "Eng": "The previous setting was restored because Windows could not update auto-start:\n{error}",
    },
    "toast_reminder_title": {
        "Vie": "Nhắc việc: {name}",
        "Eng": "Task reminder: {name}",
    },
    "toast_deadline_title": {
        "Vie": "Sắp đến hạn: {name}",
        "Eng": "Deadline soon: {name}",
    },
    "toast_deadline": {
        "Vie": "Hạn: {deadline}",
        "Eng": "Deadline: {deadline}",
    },
    "toast_priority": {
        "Vie": "Ưu tiên: {weight:.2f}",
        "Eng": "Priority: {weight:.2f}",
    },
    "toast_note": {"Vie": "Ghi chú: {note}", "Eng": "Note: {note}"},
    "toast_due_in": {
        "Vie": "Còn khoảng {minutes} phút.",
        "Eng": "Due in about {minutes} minute(s).",
    },
    "toast_note_placeholder": {
        "Vie": "Nhập ghi chú mới (để trống nếu muốn xóa ghi chú)",
        "Eng": "Enter a new note (leave blank to clear the note)",
    },
    "toast_note_caption": {
        "Vie": "Ghi chú mới:",
        "Eng": "New note:",
    },
    "toast_change": {"Vie": "Lưu ghi chú", "Eng": "Save note"},
    "toast_launch": {"Vie": "Mở tác vụ", "Eng": "Open task"},
    "toast_change_launch": {
        "Vie": "Lưu và mở",
        "Eng": "Save and open",
    },
    "toast_done": {"Vie": "Hoàn thành", "Eng": "Done"},
    "toast_progress": {
        "Vie": "Tiến độ tác vụ",
        "Eng": "Task progress",
    },
    "toast_in_progress": {
        "Vie": "Đang thực hiện",
        "Eng": "In progress",
    },
    "score_importance": {
        "Vie": "Tầm quan trọng",
        "Eng": "Importance",
    },
    "score_urgency": {
        "Vie": "Mức độ khẩn cấp",
        "Eng": "Urgency",
    },
    "score_value_roi": {
        "Vie": "Giá trị / ROI",
        "Eng": "Value / ROI",
    },
    "score_blocking": {
        "Vie": "Mức độ cản trở",
        "Eng": "Blocking",
    },
    "score_alignment": {
        "Vie": "Mức độ phù hợp",
        "Eng": "Alignment",
    },
    "score_effort": {"Vie": "Công sức", "Eng": "Effort"},
    "score_delegation": {
        "Vie": "Khả năng ủy quyền",
        "Eng": "Delegation",
    },
    "score_context": {"Vie": "Bối cảnh", "Eng": "Context"},
    "score_fatigue": {"Vie": "Mức độ mệt mỏi", "Eng": "Fatigue"},
    "score_regret": {"Vie": "Điểm hối tiếc", "Eng": "Regret Score"},
}

SCORE_KEYS = {
    "Importance": "score_importance",
    "Urgency": "score_urgency",
    "Value / ROI": "score_value_roi",
    "Blocking": "score_blocking",
    "Alignment": "score_alignment",
    "Effort": "score_effort",
    "Delegation": "score_delegation",
    "Context": "score_context",
    "Fatigue": "score_fatigue",
    "Regret Score": "score_regret",
}


COLORS: dict[Mode, dict[str, str]] = {
    "Light": {
        "window": "#f4f6fb",
        "surface": "#ffffff",
        "text": "#20283a",
        "muted": "#667085",
        "border": "#e0e5ef",
        "hover": "#edf2ff",
        "primary": "#4263eb",
        "primary_hover": "#364fc7",
        "selection": "#e9efff",
        "header": "#f7f8fc",
        "grid": "#eef0f5",
        "weekend": "#d64545",
        "selected_text": "#ffffff",
        "time_board": "#ffffff",
        "drop_down": "#ffffff",
        "scroller": "#b7b7b7"
    },
    "Dark": {
        "window": "#171a21",
        "surface": "#222630",
        "text": "#e7eaf0",
        "muted": "#a4adbd",
        "border": "#383e4b",
        "hover": "#30394d",
        "primary": "#5878f5",
        "primary_hover": "#7590ff",
        "selection": "#35446b",
        "header": "#282d38",
        "grid": "#303642",
        "weekend": "#ff7777",
        "selected_text": "#ffffff",
        "time_board": "#222630",
        "drop_down": "#222630",
        "scroller": "#a7a7a7"
    },
}


def text(key: str, language: str = "Vie", **values: object) -> str:
    selected: Language = "Eng" if language == "Eng" else "Vie"
    template = TEXTS[key][selected]
    return template.format(**values) if values else template


def colors(mode: str = "Light") -> dict[str, str]:
    selected: Mode = "Dark" if mode == "Dark" else "Light"
    return COLORS[selected].copy()


def score_label(name: str, language: str = "Vie") -> str:
    key = SCORE_KEYS.get(name)
    return text(key, language) if key is not None else name
