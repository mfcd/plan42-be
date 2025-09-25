from fastapi import FastAPI
from pydantic import BaseModel
from agent import graph

app = FastAPI(title="LangGraph FastAPI Skeleton")

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