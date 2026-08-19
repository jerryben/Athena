import httpx

from loguru import logger
from backend.core.config import settings


class EmbeddingService:
    """
    Generates vector embeddings using Ollama.
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_URL
        self.model = "nomic-embed-text:latest"

    def embed(self, text: str):
        logger.info("Generating embedding...")

        response = httpx.post(
            f"{self.base_url}/api/embeddings",
            json={
                "model": self.model,
                "prompt": text
            },
            timeout=120
        )

        logger.info("Embedding generated.")

        response.raise_for_status()

        data = response.json()

        return data["embedding"]


embedding_service = EmbeddingService()