from typing import Optional
from typing import List, Literal, Tuple
from pydantic import BaseModel, Field
from langchain_core.tools import tool, InjectedToolCallId
from langchain_core.tools.structured import StructuredTool
from langgraph.prebuilt.chat_agent_executor import AgentState
from typing import Annotated
from collections import defaultdict, deque



# Define allowed locations
Location = Literal["Apfel", "Birne", "Dattel", "Erdbeere", "Feige", "Granatapfle", "Heidelbeere"]


class Precedence(BaseModel):
    """Represents a precedence constraint: one location might need to be visited before another"""
    visit_location_before: Location
    visit_location_after: Location


def check_precedence_validity(precedences: List[Precedence]) -> Tuple[bool, Optional[List[Location]]]:
    """
    Checks if the precedence constraints are valid (no cycles).
    Returns (True, None) if valid, or (False, cycle_list) if invalid.
    """
    graph = defaultdict(list)
    nodes = set()

    # Build graph
    for p in precedences:
        before, after = p.visit_location_before, p.visit_location_after
        graph[before].append(after)
        nodes.update([before, after])

    visited = set()
    stack = set()
    path = []

    def dfs(node):
        visited.add(node)
        stack.add(node)
        path.append(node)

        for neighbor in graph[node]:
            if neighbor not in visited:
                if dfs(neighbor):
                    return True
            elif neighbor in stack:
                # Cycle found → reconstruct cycle
                cycle_start = path.index(neighbor)
                cycle = path[cycle_start:]
                cycle.append(neighbor)  # close the loop
                nonlocal found_cycle
                found_cycle = cycle
                return True

        stack.remove(node)
        path.pop()
        return False

    found_cycle = None
    for node in nodes:
        if node not in visited:
            if dfs(node):
                return False, found_cycle

    return True, None


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
    else:
        is_valid, cycle = check_precedence_validity(precedences)
        if not(is_valid):
            return {
                "success": False,
                "error": """
                    The constraints show a cycle. 
                    This means that there are some precedences that cannot be satified in light of others. 
                    """,
                "cycle": cycle
            }

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
