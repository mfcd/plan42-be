import os
from dotenv import load_dotenv

load_dotenv()  # loads .env into os.environ (for dev)
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError("Missing OPENAI_API_KEY")

from fastapi import FastAPI
from pydantic import BaseModel
from agent import graph, memory

app = FastAPI(title="Route planner demo")

@app.get("/")
async def root():
    return {"message": "LangGraph backend is running 🚀"}

@app.get("/mem")
async def return_memory():
    return memory

class ChatRequest(BaseModel):
    message: str
    user_id: str  # optional, for per-user memory

#class ChatResponse(BaseModel):
#    response: str

@app.post("/chat") #, response_model=ChatResponse)
async def chat(req: ChatRequest):
    # Send the user's message as a "user" role
    config = {"configurable": {"thread_id": req.user_id, "user_id": req.user_id}}
    result = graph.invoke(
        {"messages": [{"role": "user", "content": req.message}]},
        config=config
    )

    # The last message in the updated state is the agent's reply
    return result