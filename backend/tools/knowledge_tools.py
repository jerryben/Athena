"""Joplin and Obsidian integration tools for Athena."""

from loguru import logger

from backend.tools.registry import registry
from backend.services.joplin_service import joplin_service
from backend.services.obsidian_service import obsidian_service


# ============================================================
# JOPLIN TOOLS
# ============================================================


def joplin_get_notes(limit: int = 500) -> dict:
    """Get recent notes from Joplin. Returns up to `limit` notes."""
    result = joplin_service.search_notes("", limit=limit)
    if "error" in result:
        return {"error": result["error"], "status": "joplin_not_configured"}
    return {
        "total": len(result.get("items", [])),
        "notes": [
            {"id": n["id"], "title": n["title"], "folder_id": n.get("parent_id")}
            for n in result.get("items", [])
        ],
    }


def joplin_search_notes(query: str, limit: int = 20) -> dict:
    """Search notes in Joplin by keyword."""
    result = joplin_service.search_notes(query, limit=limit)
    if "error" in result:
        return {"error": result["error"], "status": "joplin_not_configured"}

    # Fetch body for each note to include in results
    notes = []
    for n in result.get("items", []):
        note_id = n.get("id")
        body = ""
        if note_id:
            note_result = joplin_service.get_note(note_id)
            body = note_result.get("body", "") if not note_result.get("error") else ""
        notes.append({
            "id": note_id,
            "title": n.get("title", ""),
            "body": body[:2000],  # Limit body to 2000 chars
        })

    return {
        "query": query,
        "total": len(notes),
        "notes": notes,
    }


def joplin_list_folders() -> dict:
    """List folders in Joplin."""
    result = joplin_service.list_folders()
    if "error" in result:
        return {"error": result["error"], "status": "joplin_not_configured"}
    return {
        "total": len(result.get("items", [])),
        "folders": [{"id": f["id"], "title": f["title"]} for f in result.get("items", [])],
    }


def joplin_get_note(note_id: str) -> dict:
    """Get a specific note from Joplin by ID."""
    result = joplin_service.get_note(note_id)
    if "error" in result:
        return {"error": result["error"], "status": "joplin_not_configured"}
    return {
        "id": result.get("id"),
        "title": result.get("title"),
        "body": result.get("body", ""),
        "folder_id": result.get("parent_id"),
    }


# ============================================================
# OBSIDIAN TOOLS
# ============================================================


def obsidian_search_notes(query: str, limit: int = 10) -> dict:
    """Search notes in Obsidian vault by keyword."""
    result = obsidian_service.search_notes(query, max_results=limit)
    return {
        "query": query,
        "total": result.get("count", 0),
        "notes": [
            {
                "title": n.get("path", "").replace(".md", "").split("/")[-1],
                "path": n.get("path", ""),
                "match_type": n.get("match_type", "content"),
                "preview": n.get("preview", "")[:500],
            }
            for n in result.get("results", [])
        ],
    }


def obsidian_get_note(note_path: str) -> dict:
    """Get a specific note from Obsidian vault."""
    result = obsidian_service.get_note(note_path)
    if "error" in result:
        return {"error": result["error"]}
    return {
        "path": result.get("path"),
        "title": result.get("title"),
        "content": result.get("content", "")[:5000],
    }


def obsidian_list_notes() -> dict:
    """List all notes in Obsidian vault."""
    result = obsidian_service.get_vault_stats()
    return {
        "total": result.get("stats", {}).get("total_notes", 0) if isinstance(result, dict) and "stats" in result else result.get("total_notes", 0),
        "vault_path": result.get("vault_path", ""),
        "avg_lines": result.get("avg_lines_per_note", 0),
    }


# ============================================================
# REGISTER TOOLS
# ============================================================

registry.register(
    name="joplin_get_notes",
    description="Get recent notes from Joplin. Use when user asks to list or retrieve Joplin notes.",
    parameters={
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "Number of notes to retrieve (default: 20)"},
        },
    },
    handler=joplin_get_notes,
)

registry.register(
    name="joplin_search_notes",
    description="Search notes in Joplin by keyword. Use when user asks to find specific notes.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "description": "Max results (default: 20)"},
        },
        "required": ["query"],
    },
    handler=joplin_search_notes,
)

registry.register(
    name="joplin_list_folders",
    description="List folders in Joplin. Use when user asks about Joplin folder structure.",
    parameters={
        "type": "object",
        "properties": {},
    },
    handler=joplin_list_folders,
)

registry.register(
    name="joplin_get_note",
    description="Get a specific Joplin note by ID. Use when user wants content of a specific note.",
    parameters={
        "type": "object",
        "properties": {
            "note_id": {"type": "string", "description": "Joplin note ID"},
        },
        "required": ["note_id"],
    },
    handler=joplin_get_note,
)

registry.register(
    name="obsidian_search_notes",
    description="Search notes in Obsidian vault by keyword. Use when user asks to find or search notes.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "description": "Max results (default: 10)"},
        },
        "required": ["query"],
    },
    handler=obsidian_search_notes,
)

registry.register(
    name="obsidian_get_note",
    description="Get a specific Obsidian note by file path. Use when user wants to read a specific note.",
    parameters={
        "type": "object",
        "properties": {
            "note_path": {"type": "string", "description": "Path to the note file (e.g., 'Career/Goals.md')"},
        },
        "required": ["note_path"],
    },
    handler=obsidian_get_note,
)

registry.register(
    name="obsidian_list_notes",
    description="List all notes in Obsidian vault. Use when user asks what notes exist.",
    parameters={
        "type": "object",
        "properties": {},
    },
    handler=obsidian_list_notes,
)


logger.info("Joplin and Obsidian tools registered successfully")
