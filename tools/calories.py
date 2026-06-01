import os
import sqlite3

from dotenv import load_dotenv
from langchain.tools import tool

load_dotenv()

@tool
def save_calories(food: str, calories: int) -> dict:
    """
    Save the estimated calories for a food.
    If you dont have calorie information for a food, estimate it.
    """
    try:
        conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
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
def get_todays_calories() -> dict:
    """Get the total calories consumed today."""
    try:
        conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
        cur = conn.cursor()
        query = """
        SELECT SUM(calories) 
        FROM calories 
        WHERE DATE(timestamp) = DATE('now', 'localtime')
        """
        cur.execute(query)
        result = cur.fetchone()
        conn.close()
        total_calories = result[0] if result[0] is not None else 0
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
def get_calories_ids(startDate: str, endDate: str) -> dict:
    """
    Get calorie entry IDs between two dates.
    Args:
        startDate (str): The start date in 'YYYY-MM-DD' format.
        endDate (str): The end date in 'YYYY-MM-DD' format.
    """
    try:
        conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
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
            "calorie_ids": [row[0] for row in results]
        }
    except Exception as e:
        print(f"Error fetching calorie IDs: {e}")
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
        conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
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
        conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
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