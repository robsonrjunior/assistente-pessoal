from dotenv import load_dotenv
import sqlite3
import os
from langchain.tools import tool

load_dotenv()

@tool
def set_language_preference(language: str) -> None:
    """Set the user's language preference."""
    try:
        conn = sqlite3.connect(os.getenv("PREFERENCES_DB"), check_same_thread=False)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)", ("language", language))
        conn.commit()
        conn.close()
        return {
            "status": "success",
            "message": f"Language preference set to {language}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    
@tool
def set_assistant_name(name: str) -> None:
    """Set the assistant's name."""
    try:
        conn = sqlite3.connect(os.getenv("PREFERENCES_DB"), check_same_thread=False)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)", ("assistant_name", name))
        conn.commit()
        conn.close()
        return {
            "status": "success",
            "message": f"Assistant name set to {name}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    
@tool
def set_user_name(name: str) -> None:
    """Set the user's name."""
    try:
        conn = sqlite3.connect(os.getenv("PREFERENCES_DB"), check_same_thread=False)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)", ("user_name", name))
        conn.commit()
        conn.close()
        return {
            "status": "success",
            "message": f"User name set to {name}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    
@tool
def set_user_preferred_name(preferred_name: str) -> None:
    """Set the user's preferred name."""
    try:
        conn = sqlite3.connect(os.getenv("PREFERENCES_DB"), check_same_thread=False)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO preferences (key, value) VALUES (?, ?)", ("user_preferred_name", preferred_name))
        conn.commit()
        conn.close()
        return {
            "status": "success",
            "message": f"User preferred name set to {preferred_name}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }