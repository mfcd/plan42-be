from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver
from typing import Annotated
from tools import route_validation_tool, route_solving_tool, get_available_locations_tool
from tools import RoutingAgentState
import os

memory = MemorySaver()

# Define LLM
llm = ChatOpenAI(model="gpt-4.1", temperature=0)

# Build LangGraph agent (OpenAI function-calling + your tools)
graph = create_react_agent(
    llm,
    [route_validation_tool, route_solving_tool, get_available_locations_tool],
    state_schema=RoutingAgentState,
    checkpointer=memory,
    debug=False,
    prompt="""
        Limit your role to gathering the list of locations that should be visited, and, if asked explicitly, solve the route. 
        Do not offer any other service (e.g. travel advice). Never propose to add a location to the list!
        Get the list of available location with the tool `get_available_locations_tool`.

        Always validate the list of selected locations with `route_validation_tool` and then update your status.
        Gather precedences (of two locations, which one should be visited before and which one after) and always validate them with the `route_validation_tool`. 
        
        You need a starting point. If a user gives a starting point which is not in the list of selected locations, add it to that list.

        If the user explicitly says that he wants to visit locations in a given order, sequence or with specific precedences,
        you have to gather precedences from the list. For example, the user prompt `I wanna visit locations in this order: Birne, Apfel, Dattel`
        will result in the following precedences: Birne before Apfel, and Apfel before Dattel
        Never add a precendence, if it is logically wrong.
        
        Important:
        If and *only if* the user asks explicitly to find the optimal route or estimate the distance, run `route_solving_tool`.
        Ask confirmation before running `route_solving_tool`!
        
        Whenever you return a location, wrap it in a tag `[[loc:"{Location}"]]`. For example, if the location is Rome, in your response you must always write `[[loc:"rome"]]`
    """
)