import os
from dotenv import load_dotenv
from typing import Dict
from fastapi import HTTPException, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import graph, memory
from utils.location import Location, Attraction


load_dotenv()  # loads .env into os.environ (for dev)
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError("Missing OPENAI_API_KEY")

app = FastAPI(title="Route planner demo")

#load location data from supabase
from supabase import create_client, Client
import os

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)
random_attractions = Attraction.get_random(supabase, count=5)

for a in random_attractions:
    print(f"{a.name} (ID: {a.id})")


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
    config = {"configurable": {"thread_id": req.user_id, "user_id": req.user_id}}
    result = graph.invoke(
        {"messages": [
            {"role": "user", "content": req.message},
        ]},
        config=config,
        return_intermediate_steps=True
    )
    new_messages = result["messages"][req.currently_fe_buffered_messages:]
    # The last message in the updated state is the agent's reply
    return result