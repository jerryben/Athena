"""Obsidian vault integration for Athena."""

import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger

from backend.core.config import settings
from backend.tools.registry import registry


class ObsidianService:
    """Service for interacting with Obsidian vaults."""

    def __init__(self, vault_path: str = ""):
        self.vault_path = vault_path or self._detect_vault()
        self._cache: Dict[str, str] = {}
        logger.info(f"Obsidian service initialized with vault: {self.vault_path}")

    def _detect_vault(self) -> str:
        """Try to detect Obsidian vault location."""
        possible_paths = [
            os.path.expanduser("~/Obsidian"),
            os.path.expanduser("~/Documents/Obsidian"),
            os.path.expanduser("~/Vaults/Obsidian"),
            "/home/jerry/Obsidian",
        ]

        for path in possible_paths:
            if os.path.exists(path) and os.path.isdir(path):
                # Check if it looks like an Obsidian vault
                if os.path.exists(os.path.join(path, ".obsidian")):
                    return path

        # If no .obsidian folder, check if directory has .md files
        for path in possible_paths:
            if os.path.exists(path) and os.path.isdir(path):
                md_files = list(Path(path).rglob("*.md"))
                if md_files:
                    logger.info(f"Found potential Obsidian vault at {path} with {len(md_files)} markdown files")
                    return path

        return os.path.expanduser("~/Obsidian")

    def set_vault(self, path: str):
        """Set or update the vault path."""
        self.vault_path = path
        self._cache.clear()
        logger.info(f"Obsidian vault path updated to: {path}")

    def _load_note(self, note_path: str) -> str:
        """Load a note file content."""
        full_path = os.path.join(self.vault_path, note_path)

        if full_path in self._cache:
            return self._cache[full_path]

        try:
            if os.path.exists(full_path) and full_path.endswith('.md'):
                with open(full_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._cache[full_path] = content
                return content
        except Exception as e:
            logger.error(f"Error loading note {full_path}: {e}")

        return ""

    def list_notes(self, path: str = "", max_depth: int = 3) -> Dict[str, Any]:
        """List all markdown notes in the vault."""
        try:
            search_path = os.path.join(self.vault_path, path) if path else self.vault_path

            if not os.path.exists(search_path):
                return {"error": f"Path not found: {search_path}"}

            notes = []
            for md_file in Path(search_path).rglob("*.md"):
                if md_file.depth > max_depth:
                    continue
                rel_path = md_file.relative_to(self.vault_path)
                notes.append(str(rel_path))

            return {
                "vault": self.vault_path,
                "path": path,
                "notes": notes,
                "count": len(notes),
            }
        except Exception as e:
            return {"error": str(e)}

    def search_notes(self, query: str, path: str = "", max_results: int = 20) -> Dict[str, Any]:
        """Search notes by content or filename."""
        try:
            query_lower = query.lower()
            results = []

            search_path = os.path.join(self.vault_path, path) if path else self.vault_path

            for md_file in Path(search_path).rglob("*.md"):
                rel_path = str(md_file.relative_to(self.vault_path))

                # Check filename
                if query_lower in rel_path.lower():
                    results.append({
                        "path": rel_path,
                        "match_type": "filename",
                        "preview": self._get_preview(md_file),
                    })
                    continue

                # Check content
                try:
                    content = md_file.read_text(encoding='utf-8')
                    if query_lower in content.lower():
                        results.append({
                            "path": rel_path,
                            "match_type": "content",
                            "preview": self._get_preview(md_file),
                        })
                except Exception:
                    continue

                if len(results) >= max_results:
                    break

            return {
                "query": query,
                "results": results,
                "count": len(results),
            }
        except Exception as e:
            return {"error": str(e)}

    def get_note(self, path: str) -> Dict[str, Any]:
        """Get full content of a note."""
        try:
            content = self._load_note(path)
            if not content:
                return {"error": f"Note not found: {path}"}

            return {
                "path": path,
                "content": content,
                "lines": len(content.split('\n')),
            }
        except Exception as e:
            return {"error": str(e)}

    def _get_preview(self, file_path: Path, preview_lines: int = 5) -> str:
        """Get a preview of a note's content."""
        try:
            content = file_path.read_text(encoding='utf-8')
            lines = content.split('\n')[:preview_lines]
            return '\n'.join(lines)
        except Exception:
            return ""

    def create_note(self, path: str, content: str, folder: str = "") -> Dict[str, Any]:
        """Create a new note in the vault."""
        try:
            if folder:
                full_path = os.path.join(self.vault_path, folder, path)
            else:
                full_path = os.path.join(self.vault_path, path)

            # Ensure .md extension
            if not full_path.endswith('.md'):
                full_path += '.md'

            # Create directory if needed
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Clear cache for this path
            self._cache.pop(full_path, None)

            return {
                "status": "created",
                "path": full_path,
                "relative_path": os.path.relpath(full_path, self.vault_path),
            }
        except Exception as e:
            return {"error": str(e)}

    def update_note(self, path: str, content: str) -> Dict[str, Any]:
        """Update an existing note."""
        try:
            full_path = os.path.join(self.vault_path, path)
            if not full_path.endswith('.md'):
                full_path += '.md'

            if not os.path.exists(full_path):
                return {"error": f"Note not found: {path}"}

            with open(full_path, 'w', encoding='utf-8') as f:
                f.write(content)

            self._cache.pop(full_path, None)

            return {
                "status": "updated",
                "path": full_path,
            }
        except Exception as e:
            return {"error": str(e)}

    def delete_note(self, path: str) -> Dict[str, Any]:
        """Delete a note from the vault."""
        try:
            full_path = os.path.join(self.vault_path, path)
            if not full_path.endswith('.md'):
                full_path += '.md'

            if not os.path.exists(full_path):
                return {"error": f"Note not found: {path}"}

            os.remove(full_path)
            self._cache.pop(full_path, None)

            return {
                "status": "deleted",
                "path": full_path,
            }
        except Exception as e:
            return {"error": str(e)}

    def get_vault_stats(self) -> Dict[str, Any]:
        """Get statistics about the vault."""
        try:
            all_notes = list(Path(self.vault_path).rglob("*.md"))
            total_lines = 0

            for note in all_notes[:100]:  # Sample first 100
                try:
                    total_lines += len(note.read_text(encoding='utf-8').split('\n'))
                except Exception:
                    continue

            return {
                "vault_path": self.vault_path,
                "total_notes": len(all_notes),
                "avg_lines_per_note": total_lines // max(len(all_notes), 1),
            }
        except Exception as e:
            return {"error": str(e)}


# Create global instance
obsidian_service = ObsidianService(vault_path=settings.OBSIDIAN_VAULT_PATH)
