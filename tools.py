from typing import List, Literal
from pydantic import BaseModel, Field
from langchain_core.tools.structured import StructuredTool 
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.types import Command
from langchain_core.messages import ToolMessage
from typing import Annotated
from langchain_core.tools import InjectedToolCallId


# Define allowed locations
Location = Literal["Paris", "London", "New York", "Tokyo"]


class Precedence(BaseModel):
    """Represents a precedence constraint: one location might need to be visited before another"""
    location: Location
    before: Location


# Input schema
class Route(BaseModel):
    """Represents a route - a list of destinations to be visited and their precedence"""
    locations: List[Location] = Field(
        ...,
        description="List of shop locations"
    )
    precedence: List[Precedence] = Field(
        default=[],
        description="Optional: specific if a location should be visited before another"
    )


class RoutingAgentState(AgentState):
    """All the info that will be persisted as state"""
    route: Route


def validate_route(
        route: Route,
        tool_call_id: Annotated[str, InjectedToolCallId] ) -> Command:
    "function that validates that a route is correct"
    return Command(update={
        "route": route,
        "messages": [
            ToolMessage(
                "Successfully looked up user information",
                tool_call_id=tool_call_id
            )
        ]
    })


route_validation_tool = StructuredTool.from_function(
    func=validate_route,
    args_schema=Route,
    name="route_validation_tool",
    description="Validate whether the input route (locations, location precedence) is correct"
)
