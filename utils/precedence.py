from typing import List, Tuple, Optional
from collections import defaultdict
from pydantic import BaseModel, Field
from utils.location import Location

class Precedence(BaseModel):
    """Represents a precedence constraint: one location might need to be visited before another"""
    visit_location_before: Location
    visit_location_after: Location


def check_starting_point_in_precedences(
        precedences: List[Precedence],
        starting_point: Location) -> Tuple[bool, Optional[Precedence]]:
    """
    Checks whether a list of preferences puts any Location before the starting point.
    In other words, checks whether the starting point appears as a 'visit_location_after'
    in any precedence constraint (i.e., some location must be visited before it).
    
    Returns:
        (True, None) if all precedences are fine,
        (False, precedence) if a precedence violates the starting point constraint
    """
    for p in precedences:
        if p.visit_location_after == starting_point:
            return False, p  # violation found
    return True, None  # all good


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


def check_unique_locations(
    locations: List[Location],
) -> Tuple[bool, Optional[List[Location]]]:
    """
    Checks whether a list of locations contains duplicates.
    Returns (True, None) if all unique,
    or (False, [duplicate_locations]) if duplicates are found.
    """
    seen = set()
    duplicates = set()

    for loc in locations:
        if loc in seen:
            duplicates.add(loc)
        else:
            seen.add(loc)

    if duplicates:
        return False, list(duplicates)
    return True, None
