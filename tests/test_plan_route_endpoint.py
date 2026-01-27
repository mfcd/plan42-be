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
    assert response.status_code == 200
    planned_stop = CoordsMaxMileageReach(**response.json()["planned_stop"])
    assert planned_stop.lat == pytest.approx(47.19537929153277)
    assert planned_stop.lon == pytest.approx(7.550145924658294)
    cs_on_route = response.json()["charging_stations_on_route"]
    assert len(cs_on_route) == 4
