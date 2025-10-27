from typing import List, Optional, Annotated
from itertools import product
from pydantic import BaseModel, Field
from langchain_core.tools import InjectedToolCallId
from langchain_core.tools.structured import StructuredTool
from langgraph.prebuilt.chat_agent_executor import AgentState
import pyomo.environ as pyo
from utils.location import Location, distance
from utils.precedence import Precedence, check_precedence_validity, check_unique_locations, check_starting_point_in_precedences


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

    starting_point: Location = Field(
        ...,
        description="Start location. It must be one of the locations. Ask to fill if not specified."
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


class NoStartingPointError(Exception):
    """Raised when a route has no starting point."""
    def __init__(self):
        super().__init__("The route has no starting point")


class IncorrectStartingPointInPrecedence(Exception):
    """Raised when a precedence constraint puts any location before the `starting_point` """
    def __init__(self, precedence: Precedence):
        before = precedence.visit_location_before
        after = precedence.visit_location_after
        message = f"Cannot visit {before} before {after}, the starting point"
        super().__init__(message)


def validate_route(
        locations: List[Location],
        tool_call_id: Annotated[str, InjectedToolCallId],
        starting_point: Location,
        precedences: Optional[List[Precedence]] = None):
    """
    Validates that a route is correct.

    Args:
        - locations: list of locations. 
        - precedences: optional list of precedence rules for locations.
        - starting_point: out of locations, the starting point

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

    if starting_point is None:
        raise NoStartingPointError

    is_valid, duplicates = check_unique_locations(locations)
    if not(is_valid):
        raise DuplicateLocationsError(duplicates)

    if precedences is None:
        precedences = []
    else:
        is_valid, wrong_precedence = check_starting_point_in_precedences(precedences, starting_point)
        if not(is_valid):
            raise IncorrectStartingPointInPrecedence(wrong_precedence)
        is_valid, cycle = check_precedence_validity(precedences)
        if not(is_valid):
            raise PrecedenceCycleError(cycle)

    # Return Command with ToolMessage first
    return {
        "locations": locations,
        "precedences": precedences,
        "starting_point": starting_point
        },


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
    starting_point: Location,
    precedences: Optional[List[Precedence]] = None,
):
    """Solve a TSP for the given locations and optional precedence constraints."""
    locs = locations
    N = len(locs)
    if N < 2:
        raise ValueError("Need at least 2 locations to solve a TSP.")
    if starting_point not in locs:
        raise ValueError(f"Starting point {starting_point} must be in locations.")

    # Filter distance matrix to selected locations only
    dist = {(i, j): distance[i, j] for i in locs for j in locs}

    # Create Pyomo model
    model = pyo.ConcreteModel()
    model.L = pyo.Set(initialize=locs)
    model.x = pyo.Var(model.L, model.L, domain=pyo.Binary)

    # Objective: minimize total travel distance
    model.obj = pyo.Objective(
        expr=sum(dist[i,j]*model.x[i,j] for i,j in product(model.L, model.L) if i!=j),
        sense=pyo.minimize
    )

    # Each location has exactly one incoming edge
    model.arrive_once = pyo.Constraint(
        [j for j in locs if j != starting_point],
        rule=lambda m,j: sum(m.x[i,j] for i in m.L if i != j) == 1
        )

    # Position variables for precedence only
    if precedences:
        model.u = pyo.Var(model.L, domain=pyo.NonNegativeIntegers, bounds=(0, N-1))
        model.pos_link = pyo.ConstraintList()
        model.u[starting_point].fix(0)
        # Link position to edges
        for i in locs:
            for j in locs:
                if i != j:
                    model.pos_link.add(model.u[j] >= model.u[i] + 1 - 100 * (1 - model.x[i,j]))
        
        # Precedence constraints
        model.prec = pyo.ConstraintList()
        for p in precedences:
            a, b = p.visit_location_before, p.visit_location_after
            if a in locs and b in locs:
                model.prec.add(model.u[a] + 1 <= model.u[b])

    # Solver
    if pyo.SolverFactory("glpk").available(exception_flag=False):
        solver = pyo.SolverFactory("glpk")
    elif pyo.SolverFactory("cbc").available(exception_flag=False):
        solver = pyo.SolverFactory("cbc")
    else:
        raise RuntimeError("No solver found. Please install GLPK or CBC.")

    result = solver.solve(model, tee=False)
        
    if (result.solver.status != pyo.SolverStatus.ok or
        result.solver.termination_condition != pyo.TerminationCondition.optimal):
        raise RuntimeError(
            f"Solver failed: status={result.solver.status}, "
            f"termination={result.solver.termination_condition}"
        )
    # Build edges from the solver solution
    edges = [(i, j) for i, j in product(locs, locs) if i != j and pyo.value(model.x[i, j]) > 0.5]

    # Build next_stop mapping
    next_stop = {i: j for i, j in edges}
    tour = [starting_point]
    visited = {starting_point}
    while len(tour) < len(locs):
        current = tour[-1]
        next_node = next_stop.get(current)
        remaining = set(locs) - visited
        if not next_node or next_node in visited:
            next_node = remaining.pop()
        tour.append(next_node)
        visited.add(next_node)

    return {
        "locations": locations,
        "precedences": [p.dict() for p in precedences] if precedences else [],
        "ordered_route": tour,
        "total_distance": pyo.value(model.obj),
        "positions": {i: pyo.value(model.u[i]) for i in model.L} if precedences else None
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