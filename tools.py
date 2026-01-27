from typing import List, Optional, Annotated
from itertools import product
from pydantic import BaseModel, Field
from langchain_core.tools import InjectedToolCallId
from langchain_core.tools.structured import StructuredTool
from langgraph.prebuilt.chat_agent_executor import AgentState
import pyomo.environ as pyo
from utils.location import Location, LocationDistanceMatrix
from utils.precedence import Precedence, check_precedence_validity, check_unique_locations, check_starting_point_in_precedences
from langchain_core.runnables import RunnableConfig


class RoutingAgentState(AgentState):
    """
    All the info that will be persisted as state: 
        - location: the list of location ids that will be part of a route
        - precendences: the optional list of precedences
        - the id of the starting point location
    """
    locations: List[int]
    precedences: Optional[List[Precedence]]
    starting_point: int


class PrecedenceCycleError(Exception):
    """Raised when a precedence constraint cannot be satisfied"""
    def __init__(self, cycle: List[int]):
        self.cycle = cycle
        message = f"Cycle detected in precedence constraints: {' → '.join(cycle)}"
        super().__init__(message)


class DuplicateLocationsError(Exception):
    """Raised when duplicate locations are detected in a list."""
    def __init__(self, duplicates: List[int]):
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


def get_available_locations(config: RunnableConfig):
    """Call this to see which locations are available to be added to a route."""
    locations = config["configurable"].get("eligible_locations", [])
    if not locations:
        return "No locations found."
    
    # Return a list of IDs and names
    # Note: by returning here only id and name, the model has no idea of other properties (e.g. lat, lon)
    # All the other shit is buried in the configurable
    return [
        {"id": loc.id, 
         "name": getattr(loc, 'name', loc.id)} for loc in locations
        ]


get_available_locations_tool = StructuredTool.from_function(
    func=get_available_locations,
    #args_schema=Route,  # automatically validate inputs
    name="get_available_locations",
    description="""
        Run this to get the list of all available locations
    """
)

def validate_route(
        locations: List[int],
        tool_call_id: Annotated[str, InjectedToolCallId],
        starting_point: int,
        precedences: Optional[List[Precedence]] = None):
    """
    Validates that a route is correct.
    This function only uses ids as it only looks at the sequence of ids in the route,
    and the location ids in the preferences

    Args:
        - locations: list of location ids. 
        - precedences: optional list of precedence rules for locations.
        - starting_point: out of locations, the starting point

    Important:
    The order of locations in the list `locations` does not represent the order they will be visited.
    The order will be only defined later. 
    A precedence specifies a location to visit first (visit_location_before)
    and a location to visit afterwards (visit_location_after). Example:
    
    { 
        visit_location_before: 111,
        visit_location_after: 777"
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
    route_locations: List[int],
    tool_call_id: Annotated[str, InjectedToolCallId],
    starting_point: int,
    config: RunnableConfig,
    precedences: Optional[List[Precedence]] = None
):
    """Solve a TSP for the given locations and optional precedence constraints."""
    N = len(route_locations)
    if N < 2:
        raise ValueError("Need at least 2 locations to solve a TSP.")
    if starting_point not in route_locations:
        raise ValueError(f"Starting point {starting_point} must be in the route locations.")

    # Filter distance matrix to selected locations only
    #dist = {(i, j): distance[i, j] for i in lolocationscs for j in locs}
    distance_matrix = config.get("configurable", {}).get("matrix")
    if not distance_matrix:
        return "Error: Distance Matrix was not provided in the configuration."
    dm = distance_matrix.get_distance_matrix_as_dict(route_locations)

    # Create Pyomo model
    model = pyo.ConcreteModel()
    model.L = pyo.Set(initialize=route_locations)
    model.x = pyo.Var(model.L, model.L, domain=pyo.Binary)

    # Objective: minimize total travel distance
    model.obj = pyo.Objective(
        expr=sum(dm[i,j]*model.x[i,j] for i,j in product(model.L, model.L) if i!=j),
        sense=pyo.minimize
    )

    # Each location has exactly one incoming edge
    model.arrive_once = pyo.Constraint(
        [j for j in route_locations if j != starting_point],
        rule=lambda m,j: sum(m.x[i,j] for i in m.L if i != j) == 1
        )

    # Position variables for precedence only
    if precedences:
        model.u = pyo.Var(model.L, domain=pyo.NonNegativeIntegers, bounds=(0, N-1))
        model.pos_link = pyo.ConstraintList()
        model.u[starting_point].fix(0)
        # Link position to edges
        for i in route_locations:
            for j in route_locations:
                if i != j:
                    model.pos_link.add(model.u[j] >= model.u[i] + 1 - 100 * (1 - model.x[i,j]))
        
        # Precedence constraints
        model.prec = pyo.ConstraintList()
        for p in precedences:
            a, b = p.visit_location_before, p.visit_location_after
            if a in route_locations and b in route_locations:
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
    edges = [(i, j) for i, j in product(route_locations, route_locations) if i != j and pyo.value(model.x[i, j]) > 0.5]

    # Build next_stop mapping
    next_stop = {i: j for i, j in edges}
    tour = [starting_point]
    visited = {starting_point}
    while len(tour) < len(route_locations):
        current = tour[-1]
        next_node = next_stop.get(current)
        remaining = set(route_locations) - visited
        if not next_node or next_node in visited:
            next_node = remaining.pop()
        tour.append(next_node)
        visited.add(next_node)

    return {
        "locations": route_locations,
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