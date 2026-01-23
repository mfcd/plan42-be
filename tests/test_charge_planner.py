import pytest
from utils.charge_planner import ChargePlanner
from utils.location import LocationDistanceMatrix
from utils.location import Attraction

def test_charge_planner_real_file():

    attractions = Attraction.load_list_from_json("cached_attractions.json")
    dm = LocationDistanceMatrix(attractions, filename="cached_distances.json")
    print(dm)

    # 2. Your specific test case
    ordered_route = [578, 497, 881]
    tank_limit_meters = 260000 
    
    # 3. Run the planner
    planner = ChargePlanner(ordered_route, tank_limit_meters)
    result = planner.find_last_location_before_tank(dm)
    
    # 4. Print results (visible if you run pytest with -s)
    print(f"\nLast stop before empty: {result}")
    
    # Optional: Verify against a known expected value in your file
    # assert result == 497