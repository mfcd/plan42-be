from typing import List, Optional
from utils.location import LocationDistanceMatrix

class ChargePlanner():
   def __init__(
       self,
       ordered_route: List[int],
       max_mileage: float
    ):
      if len(ordered_route) >= 2:
         self.ordered_route = ordered_route
      else:
         raise ValueError("StopPlanner requires at least two locations (incl start point)")
      self.max_mileage = max_mileage


   def find_last_location_before_tank(self, distances: LocationDistanceMatrix) -> int:
      """
         Find the last location before fuel runs out.
         Returns the id [int].
      """
      i = 1
      distance_travelled = 0
      while i < len(self.ordered_route):
         start_id = self.ordered_route[i-1]
         end_id = self.ordered_route[i]
         distance = distances.get_distance_between_ids(start_id, end_id)
         distance_travelled += distance
         if (distance_travelled <= self.max_mileage):
            i += 1
         else:
            break
      return self.ordered_route[i-1]
      





   
