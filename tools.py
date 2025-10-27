from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.tools import InjectedToolCallId
from langchain_core.tools.structured import StructuredTool
from langgraph.prebuilt.chat_agent_executor import AgentState
from typing import Annotated
from utils.location import Location
from utils.precedence import Precedence, check_precedence_validity, check_unique_locations

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


class PrecedenceCycleError(Exception):
    """Raised when a precedence constraint cannot be satisfied"""
    def __init__(self, cycle: List[str]):
        self.cycle = cycle
        message = f"Cycle detected in precedence constraints: {' → '.join(cycle)}"
        super().__init__(message)


class DuplicateLocationsError(Exception):
    """Raised when duplicate locations are detected in a list."""
    def __init__(self, duplicates: List[str]):
        self.duplicates = duplicates
        message = f"Duplicate locations detected: {', '.join(duplicates)}"
        super().__init__(message)


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

    is_valid, duplicates = check_unique_locations(locations)
    if not(is_valid):
        raise DuplicateLocationsError(duplicates)

    if precedences is None:
        precedences = []
    else:
        is_valid, cycle = check_precedence_validity(precedences)
        if not(is_valid):
            raise PrecedenceCycleError(cycle)


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
