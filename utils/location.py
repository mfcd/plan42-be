from abc import ABC
from pydantic import BaseModel, Field, HttpUrl, field_validator
from typing import List, Optional
from supabase import Client


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


distance = None