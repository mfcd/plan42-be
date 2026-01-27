import requests
import os
from utils.location import Location
from local_directions_cache import LocalDirectionsCache

class Directions():

    @classmethod
    def get_from_mapbox(
        self,
        start_loc: Location,
        end_loc: Location,
        directions_cache: LocalDirectionsCache):
        coords_str = f"{start_loc.lon},{start_loc.lat};{end_loc.lon}, {end_loc.lat}"
        mapbox_access_token = os.getenv("MAPBOX_TOKEN")
        if not mapbox_access_token:
            raise ValueError("MAPBOX_TOKEN not found in .env file.")
        url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{coords_str}"
        params = {
            "access_token": mapbox_access_token,
            "geometries": "geojson",
            "overview": "full",
            "alternatives": "false"
        }
        response = requests.get(url, params=params)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            # You can still access the Mapbox message if it exists
            error_detail = response.json().get('message', 'Unknown Mapbox Error')
            raise ValueError(f"Mapbox API Request Failed: {error_detail}") from e
        directions_cache.add(start_loc.id, end_loc.id, response.json())