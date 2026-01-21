import json

file = "ch.bfe.ladestellen-elektromobilitaet.json"

with open(file, "r", encoding="utf-8") as file:
    EVSE = json.load(file)

EVSE["EVSEData"][0]["EVSEDataRecord"][0].keys()

charging_stations = []
unique_charging_stations = {}
i = 0
for ESVE in EVSE["EVSEData"]:
    op_id = ESVE["OperatorID"]
    operator_name = ESVE["OperatorName"]
    for record in ESVE["EVSEDataRecord"]:
        i += 1
        print(i)
        address = record["Address"]
        chargingStationId = record["ChargingStationId"]
        geocoords = record["GeoCoordinates"]["Google"]
        lat = geocoords.split()[0]
        lon = geocoords.split()[1]
        EvseId = record["EvseID"]
        station_name_field = record["ChargingStationNames"]
        if station_name_field is None:
            station_name = EvseId
        elif isinstance(station_name_field, list):
            station_name = station_name_field[0]["value"]
        else:
            station_name = station_name_field["value"]
        reformatted = {
            "operator_id": op_id,
            "operator_name": operator_name,
            "address": address,
            "station_name": station_name,
            "charging_station_id": chargingStationId,
            "lat": lat,
            "lon": lon,
        }
        charging_stations.append(reformatted)
        if (lat,lon) not in unique_charging_stations:
            unique_charging_stations[(lat, lon)] = reformatted

list_of_uniques = list(unique_charging_stations.values())

from supabase import create_client, Client
import os

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)

supa_response = (
    supabase.table("charging_stations").insert(list_of_uniques).execute()
)