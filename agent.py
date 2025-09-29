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
    debug=False,
    prompt="""
        Limit your role to gathering the list of locations that should be visited.
        Keep in mind that the optimal sequence will be defined afterwards.
        Always validate the list of locations with the tool and update there your status.
        With the tool, gather the precedences (of two locations, which one should be visited before and which one after).
        Do not offer any other service (e.g. travel advice).
    """
)