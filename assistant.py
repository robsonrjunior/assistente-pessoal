from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain.messages import HumanMessage

load_dotenv()

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


def send_message(message: str) -> None:
    system_prompt = "You are a helpful assistant"
    agent = create_agent(
        model="google_genai:gemini-2.5-flash-lite",
        tools=[get_weather],
        system_prompt=system_prompt,
    )

    messages = [HumanMessage(message)]
    result = agent.invoke({"messages": messages})
    print(result["messages"][-1].content_blocks)