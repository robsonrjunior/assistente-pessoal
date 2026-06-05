from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, RemoveMessage, trim_messages
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
import os
from langchain.agents.middleware import SummarizationMiddleware, after_model, before_model, AgentState
from langchain.messages import SystemMessage
from langgraph.runtime import Runtime
from typing import Any

from pydantic import BaseModel, Field
from tools.calories import get_calories_ids, get_todays_calories, save_calories
from tools.date import get_current_datetime
from tools.preferences import set_assistant_name, set_language_preference, set_user_name
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

    return result["structured_response"].response