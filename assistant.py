from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3
import os
from langchain.agents.middleware import before_model, AgentState
from langchain.messages import SystemMessage
from langgraph.runtime import Runtime
from typing import Any
from tools.preferences import set_language_preference

load_dotenv()

def _create_preferences_table_if_not_exists():
    """Create the preferences table if it doesn't exist."""
    conn = sqlite3.connect(os.getenv("PREFERENCES_DB"), check_same_thread=False)
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

@before_model
def inject_preferences(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Inject user preferences into the agent's context before invoking the model."""
    conn = sqlite3.connect(os.getenv("PREFERENCES_DB"), check_same_thread=False)
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

    preferences_text = "\n".join(
        f"- {key}: {value}"
        for key, value in rows
    )

    system_message = SystemMessage(
        content=f"""
                User preferences:
                {preferences_text}
                """.strip()
    )

    return {
        "messages": [system_message]
    }


def send_message(message: str) -> None:
    conn = sqlite3.connect(os.getenv("CHECKPOINTER_DB"), check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    system_prompt = "You are a helpful assistant."
    agent = create_agent(
        model="google_genai:gemini-2.5-flash-lite",
        tools=[set_language_preference],
        system_prompt=system_prompt,
        checkpointer=checkpointer,
        middleware=[inject_preferences],
    )

    messages = [HumanMessage(message)]
    result = agent.invoke(
        {"messages": messages},
        {"configurable": {"thread_id": "1"}}
    )
    return result["messages"][-1].content_blocks