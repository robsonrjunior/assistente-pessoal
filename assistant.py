from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, HumanMessage, RemoveMessage, trim_messages
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
import os
from langchain.agents.middleware import SummarizationMiddleware, after_model, before_model, AgentState
from langchain.messages import SystemMessage
from langgraph.runtime import Runtime
from typing import Any
from datetime import datetime

from pydantic import BaseModel, Field
from tools.calories import get_calories_ids, get_todays_calories, save_calories
from tools.date import get_current_datetime
from tools.preferences import set_assistant_name, set_language_preference, set_user_name
from tools.scheduled_tasks import add_scheduled_task, list_scheduled_tasks, remove_scheduled_task
from langgraph.graph.message import REMOVE_ALL_MESSAGES

load_dotenv()

def _create_preferences_table_if_not_exists():
    """Create the preferences table if it doesn't exist."""
    conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()
_create_preferences_table_if_not_exists()

def _create_calories_table_if_not_exists():
    """Create the calories table if it doesn't exist."""
    conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS calories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food TEXT UNIQUE,
            calories INTEGER,
            timestamp DATETIME DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.commit()
    conn.close()
_create_calories_table_if_not_exists()


def _create_scheduled_tasks_table_if_not_exists():
    """Create the scheduled tasks table if it doesn't exist."""
    conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scheduled_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_name TEXT NOT NULL,
            task_payload TEXT,
            schedule_type TEXT NOT NULL CHECK (schedule_type IN ('cron', 'interval')),
            cron_expression TEXT,
            interval_value INTEGER,
            interval_unit TEXT CHECK (interval_unit IN ('second', 'minute', 'hour', 'day')),
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at DATETIME DEFAULT (datetime('now', 'localtime')),
            updated_at DATETIME DEFAULT (datetime('now', 'localtime')),
            CHECK (
                (schedule_type = 'cron' AND cron_expression IS NOT NULL AND interval_value IS NULL AND interval_unit IS NULL) OR
                (schedule_type = 'interval' AND cron_expression IS NULL AND interval_value IS NOT NULL AND interval_value > 0 AND interval_unit IS NOT NULL)
            )
        )
    """)
    conn.commit()
    conn.close()
_create_scheduled_tasks_table_if_not_exists()


def _create_tokens_table_if_not_exists():
    """Create the tokens table if it doesn't exist."""
    conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_day DATE NOT NULL,
            message_id TEXT NOT NULL,
            type TEXT NOT NULL CHECK (type IN ('input', 'output')),
            quantity INTEGER NOT NULL,
            created_at DATETIME DEFAULT (datetime('now', 'localtime')),
            UNIQUE(message_id, type)
        )
    """)
    conn.commit()
    conn.close()
_create_tokens_table_if_not_exists()


def _content_to_text(content: Any) -> str:
    """Normalize LangChain message content to plain text."""
    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                text_value = item.get("text")
                if isinstance(text_value, str):
                    parts.append(text_value)
        return "\n".join(parts)

    return str(content)


def _count_tokens(text: str, model: Any) -> int:
    """Count tokens using model tokenizer when available, with fallback."""
    clean_text = text or ""
    try:
        if hasattr(model, "get_num_tokens"):
            return int(model.get_num_tokens(clean_text))
    except Exception:
        pass

    # Fallback approximation when tokenizer is unavailable.
    return len(clean_text.split())


def _save_messages_tokens(messages: list[Any], model: Any) -> None:
    """Persist token counts for human/assistant messages."""
    if not messages:
        return

    rows_to_insert = []
    token_day = datetime.now().date().isoformat()

    for index, message in enumerate(messages):
        if isinstance(message, HumanMessage):
            message_type = "input"
        elif isinstance(message, AIMessage):
            message_type = "output"
        else:
            continue

        message_id = getattr(message, "id", None) or f"msg_{token_day}_{index}"
        content_text = _content_to_text(getattr(message, "content", ""))
        quantity = _count_tokens(content_text, model)
        rows_to_insert.append((token_day, str(message_id), message_type, quantity))

    if not rows_to_insert:
        return

    conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
    cur = conn.cursor()
    cur.executemany(
        """
        INSERT OR IGNORE INTO tokens (token_day, message_id, type, quantity)
        VALUES (?, ?, ?, ?)
        """,
        rows_to_insert,
    )
    conn.commit()
    conn.close()


@before_model
def trim_conversation(state, runtime):
    messages = state["messages"]

    trimmed_messages = trim_messages(
        messages=messages,
        max_tokens=20,
        token_counter=len,
        strategy="last",
        include_system=True,
        start_on="human",
    )

    has_human = any(
        isinstance(m, HumanMessage)
        for m in trimmed_messages
    )

    if not has_human:
        last_human = next(
            (
                m
                for m in reversed(messages)
                if isinstance(m, HumanMessage)
            ),
            None,
        )

        if last_human:
            trimmed_messages.append(last_human)

    if not trimmed_messages:
        return None

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *trimmed_messages,
        ]
    }


@before_model
def inject_preferences(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Inject user preferences into the agent's context before invoking the model."""
    conn = sqlite3.connect(os.getenv("ASSISTANT_DB"), check_same_thread=False)
    cur = conn.cursor()
    query = """
    SELECT key, value
    FROM preferences
    """
    cur.execute(query)
    rows = cur.fetchall()
    cur.close()
    conn.close()

    if not rows:
        return None
    
    preferences_content = ""
    
    assistant_name = next((value for key, value in rows if key == "assistant_name"), "Assistant")
    if assistant_name:
        preferences_content += f"Your name: {assistant_name}\n"

    user_language = next((value for key, value in rows if key == "language"), "English")
    if user_language:
        preferences_content += f"User language preference: {user_language}\n"

    preferences_text = "\n".join(
        f"- {key}: {value}"
        for key, value in rows
        if key != "assistant_name" and key != "language"
    )

    preferences_content += f"User preferences:\n{preferences_text}"

    system_message = SystemMessage(content=preferences_content.strip())

    return {
        "messages": [system_message]
    }

class Response(BaseModel):
    """Response from the assistant."""
    response: str = Field(description="The assistant's response")

def send_message(message: str) -> None:
    conn = sqlite3.connect(os.getenv("CHECKPOINTER_DB"), check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    system_prompt = "You are a helpful assistant."
    model = init_chat_model("google_genai:gemini-3.1-flash-lite")
    agent = create_agent(
        model=model,
        tools=[
            set_language_preference,
            set_assistant_name,
            set_user_name,
            get_current_datetime,
            save_calories,
            get_todays_calories,
            get_calories_ids,
            add_scheduled_task,
            remove_scheduled_task,
            list_scheduled_tasks,
        ],
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        middleware=[
            trim_conversation,
            inject_preferences,
        ],
        response_format=Response
    )

    messages = [HumanMessage(content=message)]
    result = agent.invoke(
        {"messages": messages},
        {"configurable": {"thread_id": "1"}}
    )

    _save_messages_tokens(result.get("messages", []), model)

    return result["structured_response"].response