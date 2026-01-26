import os
from typing import Annotated, Any
import requests
from shapely.geometry import shape, Point
from shapely import wkb
from pydantic import BaseModel, BeforeValidator, ConfigDict
from supabase import Client

# The "magic" conversion logic
def hex_to_point(v: Any) -> Point:
    """Converts a HEX EWKB to a Shapely Point"""
    return wkb.loads(v, hex=True)

# Annotated type for reuse
ShapelyPoint = Annotated[Point, BeforeValidator(hex_to_point)]

class ChargingStation(BaseModel):
    id: int
    operator_id: str
    operator_name: str 
    lat: float
    lon: float
    # Automatically becomes a Shapely Point on init
    location: ShapelyPoint

    # Tells Pydantic not to panic about the Shapely 'Point' type
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @classmethod
    def fetch_and_cache_isochrone(station, supabase: Client):
        mapbox_tkn = os.environ.get("MAPBOX_TOKEN")
        url = f"https://api.mapbox.com/isochrone/v1/mapbox/driving/{station.lon},{station.lat}"
        params = {
            "contours_minutes": 5,
            "polygons": "true",
            "access_token": mapbox_tkn
        }
        
        response = requests.get(url, params=params).json()
        
        # Mapbox returns a FeatureCollection; we take the first feature's geometry
        geojson_poly = response['features'][0]['geometry']
        shapely_poly = shape(geojson_poly)
        
        # Convert to Hex EWKB to save back to Supabase
        hex_for_db = wkb.dumps(shapely_poly, hex=True, srid=4326)
        
        # Update Supabase
        supabase.table("charging_stations").update({
            "catchment_area_5_min": hex_for_db
        }).eq("id", station.id).execute()
    

    def find_nearby_lat_lon(self, lat: float, lon: float, supabase: Client):
        return supabase.rpc('get_nearest_chargers', {
            'target_lat': lat, 
            'target_lon': lon, 
            'n_count': 5
        }).execute()


    @classmethod
    def find_by_isochrones(self, lat: float, lon: float, supabase: Client):
        return supabase.rpc(
            'get_chargers_covering_point', 
            {
                'target_lat': lat,
                'target_lon': lon
            }
        ).execute()