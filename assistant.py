from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3


load_dotenv()

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


def send_message(message: str) -> None:
    conn = sqlite3.connect("checkpointer.db", check_same_thread=False)
    checkpointer = SqliteSaver(conn)
    system_prompt = "You are a helpful assistant"
    agent = create_agent(
        model="google_genai:gemini-2.5-flash-lite",
        tools=[get_weather],
        system_prompt=system_prompt,
        checkpointer=checkpointer
    )

    messages = [HumanMessage(message)]
    result = agent.invoke(
        {"messages": messages},
        {"configurable": {"thread_id": "1"}}
    )
    print(result["messages"][-1].content_blocks)