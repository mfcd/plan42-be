from abc import ABC
from pydantic import BaseModel, Field, HttpUrl, field_validator, ConfigDict
from typing import List, Optional, Dict, Tuple
from supabase import Client
from pydantic import TypeAdapter
import json
from pathlib import Path
from pydantic import TypeAdapter
import requests
import os


class Location(BaseModel, ABC):
    model_config = ConfigDict(frozen=True)

    id: int = Field(..., description="Unique database identifier")
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    name: str = Field(..., description="Location name, easier to browse than id")

    @field_validator('lat')
    @classmethod
    def validate_lat(cls, v: float) -> float:
        if not -90 <= v <= 90:
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator('lon')
    @classmethod
    def validate_lon(cls, v: float) -> float:
        if not -180 <= v <= 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v
    
    def is_in_swiss_bbox(self) -> bool:
        """Helper method available to all child locations"""
        return 45.817 <= self.lat <= 47.808 and 5.955 <= self.lon <= 10.492


class Attraction(Location):
    myswitzerland_id: str = Field(..., description="keep the myswitzerland id!")
    photo: Optional[str] = None
    abstract: Optional[str] = None
    url: Optional[HttpUrl] = None
    photo: Optional[HttpUrl] = None


    @classmethod
    def get_random(cls, supabase: Client, count: int = 10) -> List["Attraction"]:
        """
        Fetches random attractions from Supabase and returns them as 
        a list of Attraction instances.
        """
        response = supabase.rpc("get_random_attractions", {"limit_count": count}).execute()
        
        # 'cls' refers to the Attraction class itself
        return [cls(**item) for item in response.data]
    

    @classmethod
    def save_list_to_json(cls, attractions: list["Attraction"], filename: str = "locations.json"):
        """
        Takes a list of Attraction objects and saves them to a JSON file.
        """
        # We use a TypeAdapter to handle the list of objects efficiently
        adapter = TypeAdapter(list["Attraction"])
        
        # Convert to JSON bytes (using aliases so it matches your DB/JSON keys)
        json_data = adapter.dump_json(attractions, by_alias=True, indent=4)
        
        with open(filename, "wb") as f:
            f.write(json_data)
            
        print(f"Successfully saved {len(attractions)} items to {filename}")


    @classmethod
    def load_list_from_json(cls, filename: str = "locations.json") -> list["Attraction"]:
        """
        Reads a JSON file and returns a list of Attraction objects.
        """
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [cls(**item) for item in data]
    

class LocationDistanceMatrix:
    def __init__(self,
                 locations: List[Location],
                 filename=None
        ):
        self.locations: List[Location] = locations
        # Create a lookup table to translate ID strings to matrix indices
        self.id_to_index = {loc.id: i for i, loc in enumerate(locations)}
        if filename is None: 
            self.distance_matrix_full: List[List[float]] = self._get_matrix_from_mapbox()
        else:
            self.distance_matrix_full: List[List[float]] = self._get_matrix_from_file(filename)

    def _get_coords_string(self) -> str:
        """Formats locations into the Mapbox lng,lat;lng,lat format."""
        return ";".join([f"{loc.lon},{loc.lat}" for loc in self.locations])


    def _get_matrix_from_mapbox(self, profile: str = "mapbox/driving", use_curbside: bool = False):
        """
        Queries Mapbox for the full matrix.
        :param profile: mapbox/driving, mapbox/walking, mapbox/cycling
        :param use_curbside: If True, forces arrival on the right side of the road.
        """
        access_token = os.getenv("MAPBOX_TOKEN")
        if not access_token:
            raise ValueError("MAPBOX_TOKEN not found in .env file.")
        url = f"https://api.mapbox.com/directions-matrix/v1/{profile}/{self._get_coords_string()}"
        params = {
            "access_token": access_token,
            "annotations": "distance",
            "sources": "all",
            "destinations": "all"
        }
        if use_curbside:
            params["approaches"] = ";".join(["curbside"] * len(self.locations))
        response = requests.get(url, params=params)
        response.raise_for_status()
        distances = response.json()["distances"]
        assert len(distances) == len(self.locations)
        return distances
      

    def _get_matrix_from_file(self, filename):
        with open(filename, "r", encoding="utf-8") as f:
            raw_data = json.load(f)
        return raw_data["distances"]
    

    def get_idx(self, location_id: int) -> int:
        """Public method to retrieve the index of a specific ID."""
        try:
            return self.id_to_index[location_id]
        except KeyError as exc:
            # 'from exc' preserves the original traceback
            raise KeyError(f"Location ID '{location_id}' not found!") from exc


    def get_distance_between_ids(self, id1: int, id2: int):
        idx1 = self.get_idx(id1)
        idx2 = self.get_idx(id2)
        return self.distance_matrix_full[idx1][idx2]


    def get_sub_matrix(self, subset_location_ids: List[int]) -> List[List[float]]:
        """
        Generates a distance matrix for a smaller list of locations 
        using the data from the existing larger matrix.
        """
        if not self.distance_matrix_full:
            raise ValueError("Distance matrix is empty. Load or fetch data first.")

        new_matrix = []
        for row_loc in subset_location_ids:
            row_idx = self.get_idx(row_loc)
            new_row = []
            
            for col_loc in subset_location_ids:
                col_idx = self.get_idx(col_loc)
                # Pluck the distance from the original 2D list
                new_row.append(self.distance_matrix_full[row_idx][col_idx])
            
            new_matrix.append(new_row)
            
        return new_matrix
    

    def get_distance_matrix_as_dict(self, subset_locations: List[int]) -> Dict[Tuple[int, int], float]:
        """
        Returns a dictionary mapping (id, id) tuples to distances.
        Ensures the diagonal (self-to-self) is 0.
        """
        sub_list = self.get_sub_matrix(subset_locations)
        dist_dict = {}
        
        for i, loc_i in enumerate(subset_locations):
            for j, loc_j in enumerate(subset_locations):
                # Mapbox usually returns 0 for the diagonal, but we enforce it here
                if i == j:
                    dist_dict[(loc_i, loc_j)] = 0.0
                else:
                    dist_dict[(loc_i, loc_j)] = sub_list[i][j]
                    
        return dist_dict