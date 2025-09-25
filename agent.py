from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain.memory import ConversationBufferMemory

from tools import route_validation_tool


# Define LLM
llm = ChatOpenAI(model="gpt-4.1", temperature=0)

# Build LangGraph agent (OpenAI function-calling + your tools)
graph = create_react_agent(
    llm,
    [route_validation_tool],
)
