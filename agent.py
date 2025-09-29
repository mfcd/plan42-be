from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from tools import route_validation_tool
from tools import RoutingAgentState

memory = MemorySaver()

# Define LLM
llm = ChatOpenAI(model="gpt-4.1", temperature=0)

# Build LangGraph agent (OpenAI function-calling + your tools)
graph = create_react_agent(
    llm,
    [route_validation_tool],
    state_schema=RoutingAgentState,
    checkpointer=memory,
    debug=False
)