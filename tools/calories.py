import os
import sqlite3

from dotenv import load_dotenv
from langchain.tools import tool

load_dotenv()


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

@tool
def save_calories(food: str, calories: int) -> dict:
    """
    Save the estimated calories for a food.
    If you dont have calorie information for a food, estimate it.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO calories (food, calories) VALUES (?, ?)", (food, calories))
        conn.commit()
        conn.close()
        return {
            "status": "success",
            "message": f"Calories for {food} saved."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@tool
def get_todays_total_calories() -> dict:
    """Get the total calories consumed today."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        query = """
        SELECT COALESCE(SUM(calories), 0) AS total_calories
        FROM calories 
        WHERE DATE(timestamp) = DATE('now', 'localtime')
        """
        cur.execute(query)
        result = cur.fetchone()
        conn.close()
        total_calories = result["total_calories"] if result else 0
        return {
            "status": "success",
            "total_calories": total_calories,
            "message": f"Total calories consumed today: {total_calories}"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


@tool
def get_todays_calories_items() -> dict:
    """Get today's calorie items as an array with id, calories, and food."""
    try:
        conn = _get_connection()
        cur = conn.cursor()
        query = """
        SELECT id, calories, food
        FROM calories
        WHERE DATE(timestamp) = DATE('now', 'localtime')
        ORDER BY timestamp DESC
        """
        cur.execute(query)
        results = cur.fetchall()
        conn.close()

        return {
            "status": "success",
            "items": [
                {
                    "id": row["id"],
                    "calories": row["calories"],
                    "food": row["food"],
                }
                for row in results
            ]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    

@tool
def get_calories_ids(startDate: str, endDate: str) -> dict:
    """
    Get calorie entry IDs between two dates.
    Args:
        startDate (str): The start date in 'YYYY-MM-DD' format.
        endDate (str): The end date in 'YYYY-MM-DD' format.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        query = """
        SELECT id 
        FROM calories 
        WHERE DATE(timestamp) BETWEEN DATE(?) AND DATE(?)
        """
        cur.execute(query, (startDate, endDate))
        results = cur.fetchall()
        conn.close()
        return {
            "status": "success",
            "calorie_ids": [row["id"] for row in results]
        }
    except Exception as e:
        print(f"Error fetching calorie IDs: {e}")
        return {
            "status": "error",
            "message": str(e)
        }


@tool
def get_calory(calory_id: int) -> dict:
    """
    Get a calorie entry by ID.
    Args:
        calory_id (int): The ID of the calorie entry.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("SELECT id, food, calories, timestamp FROM calories WHERE id = ?", (calory_id,))
        row = cur.fetchone()
        conn.close()

        if row is None:
            return {
                "status": "error",
                "message": f"Calorie entry {calory_id} not found."
            }

        return {
            "status": "success",
            "calory": {
                "id": row["id"],
                "food": row["food"],
                "calories": row["calories"],
                "timestamp": row["timestamp"]
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    

@tool
def edit_calory(calory_id: int, food: str, calories: int) -> dict:
    """
    Edit a calorie entry.
    Args:
        calory_id (int): The ID of the calorie entry to edit.
        food (str): The new food name.
        calories (int): The new calorie value.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("UPDATE calories SET food = ?, calories = ? WHERE id = ?", (food, calories, calory_id))
        conn.commit()
        conn.close()
        return {
            "status": "success",
            "message": f"Calorie entry {calory_id} updated."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }
    

@tool
def delete_calory(calory_id: int) -> dict:
    """
    Delete a calorie entry.
    Args:
        calory_id (int): The ID of the calorie entry to delete.
    """
    try:
        conn = _get_connection()
        cur = conn.cursor()
        cur.execute("DELETE FROM calories WHERE id = ?", (calory_id,))
        conn.commit()
        conn.close()
        return {
            "status": "success",
            "message": f"Calorie entry {calory_id} deleted."
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }