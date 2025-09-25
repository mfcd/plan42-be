from typing import List, Literal
from pydantic import BaseModel, Field
from langchain.tools import StructuredTool

# Define allowed locations
Location = Literal["Paris", "London", "New York", "Tokyo"]


class Precedence(BaseModel):
    """Represents a precedence constraint: one location might need to be visited before another"""
    location: Location
    before: Location


# Input schema
class RouteInput(BaseModel):
    """Represents a route - a list of destinations to be visited"""
    locations: List[Location] = Field(
        ..., 
        description="List of shop locations"
    )
    precedence: List[Precedence] = Field(
        default=[],
        description="Optional: specific if a location should be visited before another"
    )


def validate_route(route: RouteInput) -> bool:
    return True


route_validation_tool = StructuredTool.from_function(
    func=validate_route,
    args_schema=RouteInput,
    description="Validate whether the input is correct"
)