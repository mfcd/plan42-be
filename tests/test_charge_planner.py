import pytest
from utils.charge_planner import ChargePlanner
from utils.location import LocationDistanceMatrix
from utils.location import Attraction

def test_charge_planner_real_file():

    attractions = Attraction.load_list_from_json("cached_attractions.json")
    dm = LocationDistanceMatrix(attractions, filename="cached_distances.json")
    print(dm)

    ordered_route = [578, 497, 881]
    tank_limit_meters = [0, 116000, 260000]
    expected_results = [578, 497, 881]
    for i in range(3):
        planner = ChargePlanner(ordered_route, tank_limit_meters[i])
        result = planner.find_last_location_before_tank(dm)
        assert result == expected_results[i]