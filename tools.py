from typing import List, Optional, Annotated
from itertools import product
from pydantic import BaseModel, Field
from langchain_core.tools import InjectedToolCallId
from langchain_core.tools.structured import StructuredTool
from langgraph.prebuilt.chat_agent_executor import AgentState
import pyomo.environ as pyo
from utils.location import Location, distance
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


def solve_route(
    locations: List[Location],
    tool_call_id: Annotated[str, InjectedToolCallId],
    precedences: Optional[List[Precedence]] = None,
):
    """Solve a TSP for the given locations and optional precedence constraints."""
    from itertools import permutations
    
    locs = locations
    N = len(locs)
    if N < 2:
        raise ValueError("Need at least 2 locations to solve a TSP.")

    # Build precedence map
    prec_map = {}
    if precedences:
        for p in precedences:
            a, b = p.visit_location_before, p.visit_location_after
            if a in locs and b in locs:
                if a not in prec_map:
                    prec_map[a] = []
                prec_map[a].append(b)
    
    # Check if a tour satisfies precedence constraints
    def satisfies_precedence(tour):
        pos = {loc: i for i, loc in enumerate(tour)}
        for before, after_list in prec_map.items():
            for after in after_list:
                if pos[before] >= pos[after]:
                    return False
        return True
    
    # Try all permutations starting from first location
    best_tour = None
    best_distance = float('inf')
    
    start = locs[0]
    remaining = [loc for loc in locs if loc != start]
    
    for perm in permutations(remaining):
        tour = [start] + list(perm)
        
        # Check precedence
        if prec_map and not satisfies_precedence(tour):
            continue
        
        # Calculate distance
        total_dist = sum(distance[tour[i], tour[i+1]] for i in range(N-1))
        total_dist += distance[tour[-1], tour[0]]  # Return to start
        
        if total_dist < best_distance:
            best_distance = total_dist
            best_tour = tour
    
    if best_tour is None:
        raise RuntimeError("No valid tour found satisfying precedence constraints")
    
    return {
        "locations": locations,
        "precedences": [p.dict() for p in precedences] if precedences else [],
        "ordered_route": best_tour,
        "total_distance": best_distance
    }


route_solving_tool = StructuredTool.from_function(
    func=solve_route,
    #args_schema=Route,  # automatically validate inputs
    name="route_solving_tool",
    description="""
        Run only if explicitly instructed by the user.
        Returns the optimal route and total distance, given a valid route
    """
)