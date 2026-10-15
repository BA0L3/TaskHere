import logging
import os

from Background import BackgroundRuntime, _auto_start_of, _auto_start_on
from Database import DataBase
from Settings import Settings
from cli import CLI
from config import METADATA, TASKS_FILE, WEIGHTS, setup_logging


logger = logging.getLogger(__name__)


def main() -> int:
    setup_logging()
    logger.info("%s %s starting", METADATA["name"], METADATA["version"])
    runtime: BackgroundRuntime | None = None
    try:
        settings = Settings()
        if settings.recovery_message:
            print(f"Warning: {settings.recovery_message}")
        if os.name == "nt":
            try:
                if not settings.disable_console_close():
                    print(
                        "Warning: the console close button could not be "
                        "disabled; clicking X may exit the application."
                    )
            except OSError as exc:
                logger.exception("Could not disable the console close button")
                print(
                    "Warning: the console close button could not be disabled: "
                    f"{exc}"
                )
            try:
                if settings.auto_start:
                    _auto_start_on()
                else:
                    _auto_start_of()
            except OSError as exc:
                logger.exception("Could not synchronize Windows auto-start")
                print(
                    "Warning: the auto_start setting was saved, but Windows "
                    f"auto-start could not be updated: {exc}"
                )
        database = DataBase(TASKS_FILE)
        runtime = BackgroundRuntime(database, settings)
        cli = CLI(
            database,
            WEIGHTS,
            settings,
            stop_event=runtime.stop_event,
        )
        runtime.show_callback = cli.show_from_tray
        runtime.start()
        cli.run()
    except (KeyboardInterrupt, EOFError):
        print("\nExiting CLI...")
        logger.info("CLI stopped by user")
    except Exception as exc:
        logger.exception("CLI terminated due to an unexpected error")
        print(
            "The application could not continue. "
            "Check the error below and logs/taskshere.log for details."
        )
        print(f"{type(exc).__name__}: {exc}")
        return 1
    finally:
        if runtime is not None:
            runtime.stop()
    logger.info("CLI stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())