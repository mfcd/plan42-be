from fastapi import FastAPI
from pydantic import BaseModel
from agent import graph

import os
from dotenv import load_dotenv

app = FastAPI(title="Route planner demo")

load_dotenv()  # loads .env into os.environ (for dev)
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise RuntimeError("Missing OPENAI_API_KEY")

class ChatRequest(BaseModel):
    input: str

@app.get("/")
async def root():
    return {"message": "LangGraph backend is running 🚀"}

@app.post("/chat")
async def chat(req: ChatRequest):
    # LangGraph works by "invoking" the graph with input
    response = graph.invoke({"input": req.input})
    return {"output": response["output"]}