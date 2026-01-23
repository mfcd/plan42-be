from typing import List, Optional
from utils.location import LocationDistanceMatrix

class ChargePlanner():
   def __init__(
       self,
       ordered_route: List[int],
       max_mileage: float,
       distances: LocationDistanceMatrix
    ):
      if len(ordered_route) >= 2:
         self.ordered_route = ordered_route
      else:
         raise ValueError("StopPlanner requires at least two locations (incl start point)")
      self.max_mileage = max_mileage
      self.distances = distances

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
   
   def find_coords_of_max_mileage_reach(self):
      max_reach_location = self.find_last_location_before_tank()
      distance_covered_until_last_location_reached = self.get_cumulated_distance_until_location(max_reach_location)
      remaining_mileage = self.max_mileage - distance_covered_until_last_location_reached
      




   
