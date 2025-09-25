from langchain_core.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get current weather info for a location."""
    return f"The weather in {location} is sunny, 22°C."
