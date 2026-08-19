"""API routes for Athena AI."""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List

from backend.core.config import settings
from backend.services.qdrant_service import qdrant_service
from backend.core.llm_router import llm_router
from backend.services.embedding_service import embedding_service
from backend.services.memory_service import memory_service
from backend.services.chat_service import chat_service
from backend.services.conversation_service import conversation_service
from backend.tools.registry import registry

router = APIRouter()


class ChatRequest(BaseModel):
    prompt: str


class ChatResponse(BaseModel):
    response: str
    model: str
    done: bool
    tool_calls: list = []


@router.get("/")
def root():
    return {
        "project": "Athena",
        "version": settings.VERSION,
        "status": "running",
        "author": "Jerry",
    }


@router.get("/health")
def health():
    return {"status": "healthy"}


@router.get("/config")
def config():
    return {
        "project": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "ollama": settings.OLLAMA_URL,
        "litellm": settings.LITELLM_URL,
        "qdrant": settings.QDRANT_URL,
        "model": settings.LLM_MODEL,
    }


@router.get("/qdrant")
def qdrant():
    collections = qdrant_service.list_collections()
    return {
        "service": "Qdrant",
        "status": "healthy",
        "collections": collections.model_dump(),
    }


@router.get("/system")
def system():
    return {
        "project": "Athena AI",
        "version": settings.VERSION,
        "services": {
            "ollama": settings.OLLAMA_URL,
            "litellm": settings.LITELLM_URL,
            "qdrant": settings.QDRANT_URL,
        }
    }


@router.get("/ollama")
def ollama():
    return llm_router.health()


@router.post("/ask", response_model=ChatResponse)
def ask(request: ChatRequest):
    return chat_service.chat(request.prompt)


@router.get("/embed")
def embed(text: str):
    vector = embedding_service.embed(text)
    return {
        "dimensions": len(vector),
        "preview": vector[:10],
    }


@router.post("/memory/save")
def save_memory(text: str, metadata: dict = None):
    return memory_service.save(
        text=text,
        metadata=metadata or {"source": "manual", "type": "note"},
    )


@router.get("/memory/count")
def memory_count():
    return {"count": memory_service.count()}


@router.get("/memory/search")
def memory_search(query: str, memory_type: Optional[str] = None):
    return memory_service.search(
        query=query,
        memory_type=memory_type,
    )


@router.get("/conversation")
def conversation():
    return conversation_service.history()


@router.delete("/conversation")
def clear_conversation():
    conversation_service.clear()
    return {"status": "cleared"}


@router.delete("/memory")
def clear_memory():
    return memory_service.clear()


@router.get("/tools")
def list_tools():
    """List all available tools with their schemas."""
    tools = registry.get_tools()
    return {
        "tools": tools,
        "count": len(tools),
    }


@router.post("/tools/{tool_name}/execute")
def execute_tool(tool_name: str, arguments: dict):
    """Execute a specific tool with arguments."""
    result = registry.execute(tool_name, arguments)
    return result
