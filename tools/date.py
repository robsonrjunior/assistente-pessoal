from dotenv import load_dotenv
from langchain.tools import tool
from datetime import datetime

load_dotenv()

@tool
def get_current_datetime() -> None:
    """Get the current date and time."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")