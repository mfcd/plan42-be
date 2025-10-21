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
        Keep in mind that the optimal sequence will be defined afterwards. Hence, assume that the locations in a list can be visited in any order, unless promped otherwise.
        Always validate the list of locations with the tool and update there your status.
        With the tool, gather the precedences (of two locations, which one should be visited before and which one after).
        Do not offer any other service (e.g. travel advice).
        If the user explicitly says that he wants to visit locations in a given order, sequence or with specific precedences,
        you have to gather precedences from the list. For example, the user prompt `I wanna visit locations in this order: Birne, Apfel, Dattel`
        will result in the following precedences: Birne before Apfel, and Apfel before Dattel

        whenever you return a location, wrap it in a tag `[[loc:"{Location}"]]`. For example, if the location is Rome, in your response you must always write `[[loc:"rome"]]`
    """
)