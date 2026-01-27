import os
from dotenv import load_dotenv
from typing import Dict
from utils.location import Location, Attraction, LocationDistanceMatrix
from utils.local_directions_cache import LocalDirectionsCache
from utils.charge_planner import ChargePlanner, RouteRequest, CoordsMaxMileageReach
from utils.charging_station import ChargingStation
from utils.directions import Directions
from fastapi import HTTPException, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from supabase import create_client, Client
from pydantic import BaseModel, Field


load_dotenv()  # loads .env into os.environ (for dev)
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError("Missing OPENAI_API_KEY")

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)
source: str = os.environ.get("BOOT_DATA_FROM")
if source == "LIVE":
    attractions = Attraction.get_random(supabase, count=10)
    distance_matrix = LocationDistanceMatrix(attractions)
    #TODO: have a proper cache
    directions_cache = LocalDirectionsCache() 
elif source == "FILE":
    attractions = Attraction.load_list_from_json("cached_attractions.json")
    distance_matrix = LocationDistanceMatrix(attractions, filename="cached_distances.json")
    directions_cache = LocalDirectionsCache() 
else:
    raise RuntimeError("BOOT_DATA_FROM should be either SUPABASE or a file")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
        This function handles the startup and shutdown logic.
    """
    print("Server is starting up...")
    
    yield  # The application runs while paused here
    
    # --- Shutdown Logic (Triggered by Ctrl+C) ---
    print("Shutting down... cleaning up resources.")
    directions_cache.save_cache()


origins = [
    "http://localhost:5173",  # default Vite dev server
    "http://127.0.0.1:5173"
]
app = FastAPI(title="Entropy42 plan42", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # allow GET, POST, etc.
    allow_headers=["*"],   # allow any headers
)

from agent import graph, memory


def to_feature(item, geometry_type="Point"):
    """
    Converts a Pydantic model with lat, lon into a GeoJSON Feature.
    Extracts lat/lon for the geometry and puts everything else in properties.
    """
    # Use model_dump to get a dict, excluding the heavy Shapely object if it exists
    properties = item.model_dump(exclude={"location"}) 
    
    return {
        "type": "Feature",
        "geometry": {
            "type": geometry_type,
            "coordinates": [item.lon, item.lat]
        },
        "properties": properties
    }

@app.post("/plan-route")
async def plan_route(request: RouteRequest):
    """
    Takes a list of location IDs and a vehicle range, 
    then inserts necessary charging stops.
    """

    try:    
        ordered_route = request.ordered_route
        data_directions_for_route = []
        for i, v in enumerate(ordered_route[:-1]):
            j = i + 1
            start_loc_id = ordered_route[i]
            end_loc_id = ordered_route[j]
            if (start_loc_id, end_loc_id) not in directions_cache.directions:
                print(f"Downloading directions({ordered_route[i]}, {ordered_route[j]})")
                start_loc = next((a for a in attractions if a.id == start_loc_id), None)
                end_loc = next((a for a in attractions if a.id == end_loc_id), None)
                data = Directions.get_from_mapbox(start_loc, end_loc, directions_cache)
            else:
                data = directions_cache.directions[(start_loc_id, end_loc_id)]
            data_directions_for_route.append(data)
        line_coordinates = [
            d["routes"][0]["geometry"]["coordinates"]
            for d in data_directions_for_route
        ]

        planner = ChargePlanner(
            request.ordered_route, 
            request.max_mileage,
            distance_matrix,
            directions_cache
            )
        
        planned_stop: CoordsMaxMileageReach = planner.find_coords_of_max_mileage_reach()
        charging_stations_on_route = ChargingStation.find_by_isochrones(
            planned_stop.lat, 
            planned_stop.lon,
            supabase=supabase
        )

        return {
            "status": "success",
            "planned_stops": {
                "type": "FeatureCollection",
                "features": [
                    to_feature(planned_stop)
                ] #TODO: in the future this will be a real list 
            },
            "charging_stations_on_route": {
                "type": "FeatureCollection",
                "features": [
                    to_feature(cs) for cs in charging_stations_on_route
                ]
            },
            "route": {
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {"name": "Full Route Path "},
                    "geometry": {
                    "type": "MultiLineString",
                    "coordinates": line_coordinates
                    }
                }]
            },
        }

    except ValueError as ve:
        # Handle cases where the route is impossible with the given mileage
        raise HTTPException(status_code=400, detail=str(ve)) from ve
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error") from e


@app.get("/")
async def root():
    return {"message": "LangGraph backend is running 🚀"}


@app.get("/directions")
async def get_directions(
    origin_id: int = Query(..., description="The ID of the starting location"),
    destination_id: int = Query(..., description="The ID of the destination location")
    ):

    cached_data = directions_cache.get(origin_id, destination_id)
    if cached_data:
        return {"source": "cache", "data": cached_data}
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch directions for {origin_id}-{destination_id}"
        )


@app.delete("/memory")
async def flush_all_memory() -> Dict[str, str]:
    """
    Flush all memory - clear all checkpoints.
    """
    try:
        checkpoint_count = len(memory.storage)
        memory.storage.clear()
        
        return {
            "status": "success",
            "message": f"Flushed all memory ({checkpoint_count} checkpoints cleared)"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error flushing memory: {str(e)}") from e


class ChatRequest(BaseModel):
    message: str
    user_id: str  # optional, for per-user memory
    currently_fe_buffered_messages: int


@app.post("/chat")
async def chat(req: ChatRequest):
    # Send the user's message as a "user" role
    config = {
        "configurable": {
            "thread_id": req.user_id, 
            "user_id": req.user_id,
            "matrix": distance_matrix,
            "eligible_locations": attractions
        }}

    result = graph.invoke(
        {"messages": [
            {"role": "user", "content": req.message},
        ]},
        config=config,
        return_intermediate_steps=True
    )
    #new_messages = result["messages"][req.currently_fe_buffered_messages:]
    # The last message in the updated state is the agent's reply
    return result