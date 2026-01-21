from abc import ABC
from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import List, Optional
from supabase import Client
from pydantic import TypeAdapter
import json
from pathlib import Path
from pydantic import TypeAdapter


class Location(BaseModel, ABC):
    id: int = Field(..., description="Unique database identifier")
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")

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


# 2. Inherit from Location for your Attraction model
class Attraction(Location):
    name: str
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
    

distance = None