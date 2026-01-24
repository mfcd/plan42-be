import pytest
from utils.charge_planner import ChargePlanner
from utils.location import LocationDistanceMatrix
from utils.location import Attraction
from utils.local_directions_cache import LocalDirectionsCache


# This runs ONCE for the whole file
@pytest.fixture(scope="module")
def setup_data():
    attractions = Attraction.load_list_from_json("cached_attractions.json")
    dm = LocationDistanceMatrix(attractions, filename="cached_distances.json")
    directions_cache = LocalDirectionsCache()
    return attractions, dm, directions_cache


def test_charge_planner_real_file(setup_data):
    attractions, dm, directions_cache = setup_data
    print(dm)

    ordered_route = [578, 497, 881]
    tank_limit_meters = [0, 116000, 260000]
    expected_results = [578, 497, 881]
    for i in range(3):
        planner = ChargePlanner(ordered_route, tank_limit_meters[i], dm, directions_cache)
        result = planner.find_last_location_before_tank()
        assert result == expected_results[i]


def test_get_directions_from_cache(setup_data):
    attractions, dm, directions_cache = setup_data
    directions = directions_cache.get(578, 497)
    assert directions is not None

def test_get_cumulated_distance_until_location(setup_data):
    attractions, dm, directions_cache = setup_data
    ordered_route = [578, 497, 881]

    total_distance_covered_manual = 0
    for i in range(len(ordered_route)-1):
        total_distance_covered_manual += dm.get_distance_between_ids(
            ordered_route[i],
            ordered_route[i+1]
            )
    # Note: get_cumulated_distance_until does not check mileage!
    planner = ChargePlanner(ordered_route, 1, dm, directions_cache)
    total_distance_covered_ = planner.get_cumulated_distance_until_location(881)
    assert total_distance_covered_manual == total_distance_covered_


def test_find_coords_of_max_mileage_reach(setup_data):
    attractions, dm, directions_cache = setup_data
    ordered_route = [578, 497]

    mileage = 1.0
    planner = ChargePlanner(ordered_route, mileage, dm, directions_cache)
    coords_max_reach = planner.find_coords_of_max_mileage_reach()
    assert 1.0 == coords_max_reach["status"]["remaining_mileage_from_last_location_reached"]
    assert 578 == coords_max_reach["status"]["max_reach_location"]
    assert coords_max_reach["reached_endpoint"] == False

    mileage = 116000.0
    planner = ChargePlanner(ordered_route, mileage, dm, directions_cache)
    max_reach_location = planner.find_last_location_before_tank()
    assert max_reach_location == 497
    coords_max_reach = planner.find_coords_of_max_mileage_reach()
    assert coords_max_reach["reached_endpoint"] == True