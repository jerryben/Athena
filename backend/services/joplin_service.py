"""Joplin note integration for Athena."""

import os
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger


class JoplinService:
    """Service for interacting with Joplin via REST API."""

    def __init__(self, api_url: str = "", api_key: str = ""):
        # Joplin REST API runs on port 41184 (Clipper server) with token param
        self.api_url = api_url or os.getenv("JOPLIN_API_URL", "http://localhost:41184")
        self.api_key = api_key or os.getenv("JOPLIN_API_KEY", "")
        self.client = httpx.Client(
            base_url=self.api_url,
            timeout=30.0,
        )
        logger.info(f"Joplin service initialized at {self.api_url}")

    def _request(self, method: str, endpoint: str, params: dict = None, data: dict = None) -> Dict[str, Any]:
        """Make an API request to Joplin."""
        try:
            url = f"{self.api_url}/{endpoint.lstrip('/')}"
            request_params = params or {}

            if self.api_key:
                request_params["token"] = self.api_key

            response = self.client.request(
                method, url,
                params=request_params,
                json=data,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Joplin API error: {e.response.text}")
            return {"error": f"HTTP {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            logger.error(f"Joplin API error: {e}")
            return {"error": str(e)}

    def search_notes(self, query: str, folder_id: str = "", limit: int = 20) -> Dict[str, Any]:
        """Search notes by title or body. Handles pagination to get all matching notes."""
        all_items = []
        offset = 0
        batch_size = 100

        while True:
            params = {"limit": batch_size, "offset": offset, "body": "1"}
            if folder_id:
                params["folder_id"] = folder_id

            result = self._request("GET", "notes", params=params)
            if "error" in result:
                return result

            items = result.get("items", [])
            all_items.extend(items)

            # Stop if no more pages or we've reached the requested limit
            if not result.get("has_more", False) or len(all_items) >= limit * 2:  # Fetch more for filtering
                break

            offset += batch_size

        # Client-side filtering since Joplin API doesn't filter properly
        filtered_items = []
        query_lower = query.lower() if query else ""

        for item in all_items:
            # Check if matches query
            title = (item.get("title") or "").lower()
            body = (item.get("body") or "").lower()

            if query_lower:
                # Filter by query in title or body
                if query_lower in title or query_lower in body:
                    filtered_items.append(item)
            else:
                # No query = return all
                filtered_items.append(item)

            if len(filtered_items) >= limit:
                break

        return {
            "total": len(filtered_items),
            "items": filtered_items[:limit],
        }

    def get_note(self, note_id: str) -> Dict[str, Any]:
        """Get a specific note by ID."""
        return self._request("GET", f"notes/{note_id}")

    def list_folders(self, parent_id: str = "") -> Dict[str, Any]:
        """List folders in Joplin."""
        params = {}
        if parent_id:
            params["parent_id"] = parent_id
        return self._request("GET", "folders", params=params)

    def create_note(self, title: str, body: str, folder_id: str = "", tags: List[str] = None) -> Dict[str, Any]:
        """Create a new note."""
        data = {"title": title, "body": body}
        if folder_id:
            data["folder_id"] = folder_id
        if tags:
            data["tags"] = tags
        return self._request("POST", "notes", data=data)

    def update_note(self, note_id: str, title: str = None, body: str = None, folder_id: str = None) -> Dict[str, Any]:
        """Update an existing note."""
        data = {}
        if title:
            data["title"] = title
        if body:
            data["body"] = body
        if folder_id:
            data["folder_id"] = folder_id
        return self._request("PUT", f"notes/{note_id}", data=data)

    def delete_note(self, note_id: str) -> Dict[str, Any]:
        """Delete a note."""
        return self._request("DELETE", f"notes/{note_id}")

    def get_recent_notes(self, days: int = 7, limit: int = 10) -> Dict[str, Any]:
        """Get recently modified notes."""
        params = {
            "order": "updated_time",
            "order_direction": "desc",
            "limit": limit,
        }
        return self._request("GET", "notes", params=params)

    def search_by_tag(self, tag: str) -> Dict[str, Any]:
        """Search notes by tag."""
        tags = self._request("GET", "tags", params={"q": tag})
        if "error" in tags:
            return tags

        tag_id = None
        for t in tags.get("items", []):
            if t.get("title", "").lower() == tag.lower():
                tag_id = t.get("id")
                break

        if not tag_id:
            return {"error": f"Tag not found: {tag}"}

        return self._request("GET", f"tags/{tag_id}/notes")

    def get_status(self) -> Dict[str, Any]:
        """Check Joplin REST API connectivity."""
        try:
            result = self._request("GET", "notes", params={"limit": 1})
            if "error" in result:
                return {
                    "status": "not_configured",
                    "message": f"Joplin API error: {result['error']}",
                    "url": self.api_url,
                }
            return {
                "status": "connected",
                "message": f"Joplin REST API connected at {self.api_url}",
                "url": self.api_url,
                "notes_count": len(result.get("items", [])),
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "url": self.api_url,
            }


# Global instance
joplin_service = JoplinService()
