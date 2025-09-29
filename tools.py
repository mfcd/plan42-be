from typing import Optional
from typing import List, Literal
from pydantic import BaseModel, Field
from langchain_core.tools import tool, InjectedToolCallId
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
    visit_location_before: Location
    visit_location_after: Location


# Input schema
class Route(BaseModel):
    """Represents a route - a list of destinations to be visited and their precedences"""
    locations: List[Location] = Field(
        ...,
        description="List of shop locations"
    )
    precedences: List[Precedence] = Field(
        default=[],
        description="Optional: precedences define, for a pair of locations, which one should be visited first"
    )


class RoutingAgentState(AgentState):
    """All the info that will be persisted as state"""
    locations: List[Location]
    precedences: Optional[List[Precedence]]


def validate_route(
        locations: List[Location],
        tool_call_id: Annotated[str, InjectedToolCallId], 
        precedences: Optional[List[Precedence]] = None):
    """
    Validates that a route is correct.

    Args:
        - locations: list of locations. 
        - precedences: optional list of precedence rules for locations.

    Important:
    The order of locations in the list `locations` does not represent the order they will be visited.
    The order will be only defined later. 
    A precedence specifies a location to visit first (visit_location_before)
    and a location to visit afterwards (visit_location_after). Example:
    
    { 
        visit_location_before: "Rome",
        visit_location_after: "Paris"
    }

    means that you have to visit Rome before Paris.

            
    """
    # Always provide tool_call_id if available
    if precedences is None:
        precedences = []

    #tm = ToolMessage(
    #    content="Successfully validated route",
    #    artifact={"locations": locations, "precedence": precedence},
    #    tool_call_id=tool_call_id
    #)

    # Return Command with ToolMessage first
    return {"locations": locations, "precedences": precedences},


route_validation_tool = StructuredTool.from_function(
    func=validate_route,
    #args_schema=Route,
    name="route_validation_tool",
    description="""
        Validate whether the input route (locations, location precedences) is correct.        
        """
)
