import os
from dotenv import load_dotenv
from typing import Dict
from fastapi import HTTPException, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from utils.location import Location, Attraction, LocationDistanceMatrix
from utils.local_directions_cache import LocalDirectionsCache
from supabase import create_client, Client


load_dotenv()  # loads .env into os.environ (for dev)
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError("Missing OPENAI_API_KEY")

from agent import graph, memory

app = FastAPI(title="Route planner demo")

source: str = os.environ.get("BOOT_DATA_FROM")
if source == "LIVE":
    url: str = os.environ.get("SUPABASE_URL")
    key: str = os.environ.get("SUPABASE_KEY")
    supabase: Client = create_client(url, key)
    attractions = Attraction.get_random(supabase, count=10)
    #TODO: get distance matrix
    #TODO: initialize directions
elif source == "FILE":
    attractions = Attraction.load_list_from_json("cached_attractions.json")
    distance_matrix = LocationDistanceMatrix(attractions, filename="cached_distances.json")
    directions_cache = LocalDirectionsCache()
else:
    raise RuntimeError("BOOT_DATA_FROM should be either SUPABASE or a file")



origins = [
    "http://localhost:5173",  # default Vite dev server
    "http://127.0.0.1:5173"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],   # allow GET, POST, etc.
    allow_headers=["*"],   # allow any headers
)

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
        raise HTTPException(status_code=500, detail=f"Error flushing memory: {str(e)}")


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