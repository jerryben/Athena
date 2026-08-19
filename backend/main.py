"""FastAPI application for Athena AI."""

import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router
from backend.core.logging import logger
from backend.tools.registry import registry
from backend.services.obsidian_service import obsidian_service
from backend.services.joplin_service import joplin_service
from backend.services.transcription_service import transcription_service
from backend.core.config import settings

# Import to register tools
import backend.tools.knowledge_tools  # noqa: F401

app = FastAPI(
    title="Athena AI",
    version="0.2.0",
    description="Personal AI Chief of Staff with Voice & Tool Calling",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.on_event("startup")
async def startup():
    logger.info("Athena AI is starting...")
    logger.info(f"Model: {os.getenv('LLM_MODEL', 'QwenPaw-Flash-4B-Q4_K_M')}")
    logger.info(f"Tools registered: {[t['function']['name'] for t in registry.get_tools()]}")

    # Log Obsidian vault path
    logger.info(f"Obsidian vault: {obsidian_service.vault_path}")


@app.on_event("shutdown")
async def shutdown():
    logger.info("Athena AI is shutting down...")


# ============================================================
# VOICE TRANSCRIPTION ENDPOINTS
# ============================================================

@app.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("en"),
):
    """Transcribe audio file to text."""
    logger.info(f"Transcribing audio: {file.filename}, language: {language}")

    audio_data = await file.read()

    result = transcription_service.transcribe_audio(audio_data, language)

    if "error" in result:
        return {"error": result["error"]}

    return {
        "text": result["text"],
        "language": result.get("language", language),
    }


@app.post("/transcribe/url")
async def transcribe_url(url: str, language: str = "en"):
    """Download and transcribe audio from URL."""
    import httpx

    async with httpx.AsyncClient() as client:
        response = await client.get(url, timeout=60)
        if response.status_code != 200:
            return {"error": f"Failed to download audio: HTTP {response.status_code}"}

        result = transcription_service.transcribe_audio(response.content, language)

        if "error" in result:
            return {"error": result["error"]}

        return {
            "text": result["text"],
            "language": result.get("language", language),
        }


# ============================================================
# OBSIDIAN ENDPOINTS
# ============================================================

@app.get("/obsidian/vault")
def get_obsidian_vault():
    """Get Obsidian vault info."""
    return {
        "vault_path": obsidian_service.vault_path,
        "stats": obsidian_service.get_vault_stats(),
    }


@app.get("/obsidian/notes")
def list_obsidian_notes(path: str = "", max_depth: int = 3):
    """List notes in Obsidian vault."""
    return obsidian_service.list_notes(path, max_depth)


@app.get("/obsidian/search")
def search_obsidian_notes(query: str, path: str = "", max_results: int = 20):
    """Search notes in Obsidian vault."""
    return obsidian_service.search_notes(query, path, max_results)


@app.get("/obsidian/note/{note_path:path}")
def get_obsidian_note(note_path: str):
    """Get a specific note from Obsidian vault."""
    return obsidian_service.get_note(note_path)


@app.post("/obsidian/note")
def create_obsidian_note(
    path: str = Form(...),
    content: str = Form(...),
    folder: str = Form(""),
):
    """Create a new note in Obsidian vault."""
    return obsidian_service.create_note(path, content, folder)


@app.put("/obsidian/note/{note_path:path}")
def update_obsidian_note(note_path: str, content: str = Form(...)):
    """Update an existing note in Obsidian vault."""
    return obsidian_service.update_note(note_path, content)


@app.delete("/obsidian/note/{note_path:path}")
def delete_obsidian_note(note_path: str):
    """Delete a note from Obsidian vault."""
    return obsidian_service.delete_note(note_path)


# ============================================================
# JOPLIN ENDPOINTS
# ============================================================

@app.get("/joplin/notes")
def list_joplin_notes(limit: int = 20):
    """List recent notes from Joplin."""
    return joplin_service.get_recent_notes(limit=limit)


@app.get("/joplin/search")
def search_joplin_notes(query: str, limit: int = 20):
    """Search notes in Joplin."""
    return joplin_service.search_notes(query, limit=limit)


@app.get("/joplin/status")
def get_joplin_status():
    """Check Joplin REST API connection status."""
    return joplin_service.get_status()


@app.get("/joplin/folders")
def list_joplin_folders():
    """List folders in Joplin."""
    return joplin_service.list_folders()


@app.get("/joplin/note/{note_id}")
def get_joplin_note(note_id: str):
    """Get a specific note from Joplin."""
    return joplin_service.get_note(note_id)


@app.post("/joplin/note")
def create_joplin_note(
    title: str = Form(...),
    body: str = Form(""),
    folder_id: str = Form(""),
):
    """Create a new note in Joplin."""
    return joplin_service.create_note(title, body, folder_id)


@app.put("/joplin/note/{note_id}")
def update_joplin_note(
    note_id: str,
    title: str = Form(None),
    body: str = Form(None),
):
    """Update a note in Joplin."""
    return joplin_service.update_note(note_id, title, body)


@app.delete("/joplin/note/{note_id}")
def delete_joplin_note(note_id: str):
    """Delete a note from Joplin."""
    return joplin_service.delete_note(note_id)
