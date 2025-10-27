from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from tools import route_validation_tool, route_solving_tool
from tools import RoutingAgentState

memory = MemorySaver()

# Define LLM
llm = ChatOpenAI(model="gpt-4.1", temperature=0)

# Build LangGraph agent (OpenAI function-calling + your tools)
graph = create_react_agent(
    llm,
    [route_validation_tool, route_solving_tool],
    state_schema=RoutingAgentState,
    checkpointer=memory,
    debug=False,
    prompt="""
        Limit your role to gathering the list of locations that should be visited, and then, if asked explicitly, solve the route. 
        Do not offer any other service (e.g. travel advice).

        Always validate the list of locations with `route_validation_tool` and update there your status.
        With the tool, gather the precedences (of two locations, which one should be visited before and which one after).
        
        If the user explicitly says that he wants to visit locations in a given order, sequence or with specific precedences,
        you have to gather precedences from the list. For example, the user prompt `I wanna visit locations in this order: Birne, Apfel, Dattel`
        will result in the following precedences: Birne before Apfel, and Apfel before Dattel

        You need a starting point. If a user gives a starting point which is not in the list of locations, add it to it.
        
        Important:
        If and *only if* the user asks explicitly to find the optimal route or estimate the distance, run `route_solving_tool`.
        Ask confirmation before running `route_solving_tool`!
        
        Whenever you return a location, wrap it in a tag `[[loc:"{Location}"]]`. For example, if the location is Rome, in your response you must always write `[[loc:"rome"]]`
    """
)