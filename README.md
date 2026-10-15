# | TasksHere | ![1792077820787](Datas/TaskHere.png)  |
| --------- | ------------------------------------- |



TasksHere is a task manager (actually it s"Real-Life Works" Manager) for Windows 10 and Windows 11. It provides both a
command-line interface (CLI) and a graphical interface (GUI), and automatically
orders tasks by a calculated priority score.

## Features

- Create, update, list, and remove tasks.
- Score each task using ten criteria and set a deadline and optional note.
- Keep tasks sorted from highest to lowest priority.
- Use reminders, deadline alerts, and a Windows system-tray icon.
- Choose the interface language and appearance in the application settings. (EngLish and Tiếng Việt are supported))

## Getting started

### Requirements

- Windows 10 or Windows 11
- Python 3.10 or later

Install the application dependencies:

```powershell
python -m pip install PySide6 prompt_toolkit pystray Pillow windows-toasts
```

### Start the application

Run these commands from the project directory:

```powershell
# Command-line interface
python main.py

# Graphical interface
python main_gui.py
```

### Use the CLI

At the `tasks>` prompt, enter one of these commands:

| Command              | Action                                                                   |
| -------------------- | ------------------------------------------------------------------------ |
| `add`              | Create a task by entering its name, scores, deadline, and optional note. |
| `list`             | Show tasks sorted by priority.                                           |
| `update`           | Change a task's details.                                                 |
| `remove`           | Delete a task.                                                           |
| `settings`         | View or change application settings.                                     |
| `help`             | Show the available commands.                                             |
| `exit` or `quit` | Close the CLI.                                                           |

For each task, rate the first nine criteria from 1 to 5, then provide a Regret
Score from 1 to 5. Enter a future deadline when prompted. In the GUI, use the
task controls to add or edit tasks; the score inputs use the same 1-to-5 scale
and the deadline picker only accepts a date and time.

## Data and settings

The application stores task data in `Datas/Tasks.json` and settings in
`Datas/settings.json`. Logs are written to `Datas/logs/taskshere.log`. Keep the
`Datas` directory alongside the application files so the image, icon, and saved
data remain available.


Created & Developed by: BA0L3 (Lê Nguyễn Gia Bảo)
