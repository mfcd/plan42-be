import pytest
from fastapi.testclient import TestClient
from main import app
from utils.charge_planner import CoordsMaxMileageReach
from utils.charging_station import ChargingStation

# Create a fixture for the TestClient
@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_plan_route_success(client):
    payload = {
        "ordered_route": [578, 497, 881],
        "max_mileage": 90000
    }

    response = client.post("/plan-route", json=payload)
    
    # 1. Check basic status
    assert response.status_code == 200
    data = response.json()

    # 2. Assert on the "route" (The MultiLineString)
    # Ensure it's a valid FeatureCollection and has at least one MultiLineString feature
    assert data["route"]["type"] == "FeatureCollection"
    assert len(data["route"]["features"]) > 0
    assert len(data["route"])
    assert data["route"]["features"][0]["geometry"]["type"] == "MultiLineString"

    # 3. Assert on the "stops" (The Attraction points)
    # The planned stop is likely the first or last stop in this collection
    assert data["planned_stops"]["type"] == "FeatureCollection"
    
    # Let's find the specific planned stop coords in the GeoJSON structure
    # Based on your previous logic, it might be in 'stops' or a separate 'planned_stop' key
    # If it's the first feature in stops:
    planned_stop_feature = data["planned_stops"]["features"][0]
    coords = planned_stop_feature["geometry"]["coordinates"]
    
    # Note: GeoJSON is [longitude, latitude]
    assert coords[1] == pytest.approx(47.19537929153277) # Latitude
    assert coords[0] == pytest.approx(7.550145924658294) # Longitude

    # 4. Assert on "chargers" (The Charging Stations)
    assert data["charging_stations_on_route"]["type"] == "FeatureCollection"
    cs_features = data["charging_stations_on_route"]["features"]
    assert len(cs_features) == 4
    
    # You can also verify that properties were mapped correctly
    assert "operator_name" in cs_features[0]["properties"]
