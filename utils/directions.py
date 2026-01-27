import requests
import os
from utils.location import Location
from utils.local_directions_cache import LocalDirectionsCache
from fastapi import HTTPException, status

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
        
        try:
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                error_msg = response.json().get('message', 'Unknown Mapbox Error')
                # Map external 4xx errors to a 400 (Bad Request) for your client
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Mapbox API Error: {error_msg}"
                )
            
            data = response.json()
            directions_cache.add(start_loc.id, end_loc.id, data)
            return data

        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Mapbox service unreachable: {str(e)}"
            ) from e