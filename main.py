import logging
import os
import threading
from logging.handlers import RotatingFileHandler

from dotenv import load_dotenv

from assistant import send_message
from gateways.telegram_gateway import run_telegram_gateway
from scheduled_tasks.scheduled_tasks_loop import run_scheduled_tasks_loop


load_dotenv()


def _configure_logging() -> None:
    logs_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(logs_dir, exist_ok=True)

    handler = RotatingFileHandler(
        filename=os.path.join(logs_dir, "app.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(handler)


_configure_logging()

def _start_background_threads() -> None:
    threading.Thread(target=run_telegram_gateway, daemon=True, name="telegram-gateway").start()
    threading.Thread(target=run_scheduled_tasks_loop, daemon=True, name="scheduled-tasks-loop").start()


def main():
    _start_background_threads()

    if not os.getenv("RUN_INTERACTIVE_CONSOLE", "true").lower() == "true":
        threading.Event().wait()
        return

    while True:
        input_message = input("You: ")
        if input_message.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break
        response = send_message(input_message)
        print(f"Assistant: {response}")


if __name__ == "__main__":
    main()
