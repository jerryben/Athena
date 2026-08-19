from pathlib import Path
import json

from loguru import logger

HISTORY_FILE = Path("storage/chat_history.json")


class ChatHistoryService:

    def __init__(self):

        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)

        if not HISTORY_FILE.exists():
            HISTORY_FILE.write_text("[]")

    def load(self):

        try:
            history = json.loads(HISTORY_FILE.read_text())

            logger.info(f"Loaded {len(history)} chat messages")

            return history

        except Exception:

            logger.exception("Failed loading history")

            return []

    def save(self, history):

        HISTORY_FILE.write_text(
            json.dumps(
                history,
                indent=2
            )
        )

        logger.info(
            f"Saved {len(history)} chat messages"
        )

    def clear(self):

        HISTORY_FILE.write_text("[]")


chat_history_service = ChatHistoryService()