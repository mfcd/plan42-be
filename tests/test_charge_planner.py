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