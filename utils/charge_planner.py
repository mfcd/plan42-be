from typing import List, Optional
from utils.location import LocationDistanceMatrix
from utils.local_directions_cache import LocalDirectionsCache
from shapely.geometry import LineString
from pydantic import BaseModel, Field


# Define the request structure that will be used on the API 
# that runs the ChargePlanner in FASTAPI
class RouteRequest(BaseModel):
	# IDs starting at 1 are attractions, 1,000,000+ are chargers
	ordered_route: List[int] = Field(..., example=[101, 102, 103], min_items=2)
	max_mileage: float = Field(..., gt=0, example=250.0)

class CoordsMaxMileageReach(BaseModel):
    lat: Optional[float] = Field(default=None, description="Latitude")
    lon: Optional[float] = Field(default=None, description="Longitude")
    reached_endpoint: bool
    remaining_mileage_from_last_location_reached: float
    max_reach_location: int

class ChargePlanner():
	def __init__(
       self,
       ordered_route: List[int],
       max_mileage: float,
       distances: LocationDistanceMatrix,
       directions_cache: LocalDirectionsCache
    ):
		if len(ordered_route) >= 2:
			self.ordered_route = ordered_route
		else:
			raise ValueError("StopPlanner requires at least two locations (incl start point)")
		self.max_mileage = max_mileage
		self.distances = distances
		self.directions_cache = directions_cache
   
	def get_cumulated_distance_until_location(self, location:int):
		location_idx = self.ordered_route.index(location)
		if location_idx == 0:
			return 0
		else:
			distance_covered = 0
			for i in range(location_idx):
				j = i + 1
				distance_between_locations = self.distances.get_distance_between_ids(
            		self.ordered_route[i],
            		self.ordered_route[j]
            	)
				distance_covered += distance_between_locations
			return distance_covered

	def find_last_location_before_tank(self) -> int:
		"""
		Find the last location before fuel runs out.
		Returns the id [int].
		"""
		i = 1
		distance_travelled = 0
		while i < len(self.ordered_route):
			start_id = self.ordered_route[i-1]
			end_id = self.ordered_route[i]
			distance = self.distances.get_distance_between_ids(start_id, end_id)
			distance_travelled += distance
			if (distance_travelled <= self.max_mileage):
				i += 1
			else:
				break
		return self.ordered_route[i-1]

	def find_coords_of_max_mileage_reach(self) -> CoordsMaxMileageReach:
		# find the last location you can reach with the charge
		max_reach_location = self.find_last_location_before_tank()
		max_reach_location_idx = self.ordered_route.index(max_reach_location)
		
		if max_reach_location_idx == len(self.ordered_route) - 1:
			cumulated_distance = self.get_cumulated_distance_until_location(max_reach_location)
			return CoordsMaxMileageReach(
				reached_endpoint=True,
				remaining_mileage_from_last_location_reached=self.max_mileage-cumulated_distance,
				max_reach_location=max_reach_location
			)
		else:
			# calculate much distance has been covered from the start point to the last location
			distance_covered_until_last_location_reached = self.get_cumulated_distance_until_location(max_reach_location)
			# calculate how much mileage is left since the last location
			remaining_mileage = self.max_mileage - distance_covered_until_last_location_reached
			# check if the current direction tuple (max reach, and the following) is cached
			next_location_on_route_idx = max_reach_location_idx + 1
			next_location = self.ordered_route[next_location_on_route_idx]
			d = self.directions_cache.get(max_reach_location, next_location)
			if d is None:
				raise ValueError(f"{max_reach_location},{next_location} not in cache")
			geojson_geometry = d["routes"][0]["geometry"]
			line = LineString(geojson_geometry['coordinates'])
			distance_between_locations = d["routes"][0]["distance"]
			ratio = remaining_mileage / distance_between_locations
			point = line.interpolate(ratio, normalized=True)
			return CoordsMaxMileageReach(
				lat=point.y,
				lon=point.x,
				reached_endpoint=False,
				remaining_mileage_from_last_location_reached=remaining_mileage,
				max_reach_location=max_reach_location
			)  




   
