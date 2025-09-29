import os
from dotenv import load_dotenv

load_dotenv()  # loads .env into os.environ (for dev)
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError("Missing OPENAI_API_KEY")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from agent import graph, memory

app = FastAPI(title="Route planner demo")

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

@app.get("/mem")
async def return_memory():
    return memory

class ChatRequest(BaseModel):
    message: str
    user_id: str  # optional, for per-user memory
    currently_fe_buffered_messages: int

#class ChatResponse(BaseModel):
#    response: str

@app.post("/chat") #, response_model=ChatResponse)
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