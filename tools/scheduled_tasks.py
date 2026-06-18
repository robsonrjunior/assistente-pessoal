import os
import sqlite3
from typing import Literal

from dotenv import load_dotenv
from langchain.tools import tool

load_dotenv()

ScheduleType = Literal["cron", "interval", "intervalo"]
IntervalUnit = Literal[
    "minute",
    "minutes",
    "minuto",
    "minutos",
    "hour",
    "hours",
    "hora",
    "horas",
    "day",
    "days",
    "dia",
    "dias",
]


@tool
def add_scheduled_task(
    task_name: str,
    schedule_type: ScheduleType,
    cron_expression: str | None = None,
    interval_value: int | None = None,
    interval_unit: IntervalUnit | None = None,
    task_payload: str | None = None,
) -> dict:
    """
    Add a scheduled task.

    Supports:
    - schedule_type='cron' with cron_expression
    - schedule_type='interval' or 'intervalo' with interval_value and interval_unit
          (minute/hour/day or minuto/hora/dia)
    """
    try:
        normalized_schedule_type: Literal["cron", "interval"] = (
            "interval" if schedule_type == "intervalo" else schedule_type
        )

        normalized_interval_unit: Literal["minute", "hour", "day"] | None = None
        if interval_unit in ("minute", "minutes", "minuto", "minutos"):
            normalized_interval_unit = "minute"
        elif interval_unit in ("hour", "hours", "hora", "horas"):
            normalized_interval_unit = "hour"
        elif interval_unit in ("day", "days", "dia", "dias"):
            normalized_interval_unit = "day"

        if normalized_schedule_type == "cron":
            if not cron_expression:
                return {
                    "status": "error",
                    "message": "cron_expression is required when schedule_type is 'cron'.",
                }
            interval_value = None
            normalized_interval_unit = None

        if normalized_schedule_type == "interval":
            if interval_value is None or interval_value <= 0:
                return {
                    "status": "error",
                    "message": "interval_value must be greater than 0 when schedule_type is 'interval'.",
                }
            if not normalized_interval_unit:
                return {
                    "status": "error",
                    "message": "interval_unit is required for interval scheduling (minute, hour, day).",
                }
            cron_expression = None

        conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO scheduled_tasks (
                task_name,
                task_payload,
                schedule_type,
                cron_expression,
                interval_value,
                interval_unit
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                task_name,
                task_payload,
                normalized_schedule_type,
                cron_expression,
                interval_value,
                normalized_interval_unit,
            ),
        )
        conn.commit()
        task_id = cur.lastrowid
        conn.close()

        return {
            "status": "success",
            "task_id": task_id,
            "message": f"Scheduled task {task_id} added.",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


@tool
def remove_scheduled_task(task_id: int) -> dict:
    """Remove a scheduled task by ID."""
    try:
        conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
        cur = conn.cursor()
        cur.execute("DELETE FROM scheduled_tasks WHERE id = ?", (task_id,))
        conn.commit()
        deleted_rows = cur.rowcount
        conn.close()

        if deleted_rows == 0:
            return {
                "status": "error",
                "message": f"Scheduled task {task_id} not found.",
            }

        return {
            "status": "success",
            "message": f"Scheduled task {task_id} removed.",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }


@tool
def list_scheduled_tasks() -> dict:
    """List all scheduled tasks."""
    try:
        conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                id,
                task_name,
                task_payload,
                schedule_type,
                cron_expression,
                interval_value,
                interval_unit,
                is_active,
                created_at,
                updated_at
            FROM scheduled_tasks
            ORDER BY id ASC
            """
        )
        rows = cur.fetchall()
        conn.close()

        tasks = [
            {
                "id": row[0],
                "task_name": row[1],
                "task_payload": row[2],
                "schedule_type": row[3],
                "cron_expression": row[4],
                "interval_value": row[5],
                "interval_unit": row[6],
                "is_active": bool(row[7]),
                "created_at": row[8],
                "updated_at": row[9],
            }
            for row in rows
        ]

        return {
            "status": "success",
            "scheduled_tasks": tasks,
            "count": len(tasks),
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
        }