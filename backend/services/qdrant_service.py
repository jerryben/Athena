from loguru import logger

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from backend.core.config import settings
from backend.core.constants import (
    MEMORY_COLLECTION,
    EMBEDDING_DIMENSIONS,
)


class QdrantService:

    def __init__(self):

        self.client = QdrantClient(url=settings.QDRANT_URL)

        logger.info(f"Connected to Qdrant ({settings.QDRANT_URL})")

        self.ensure_memory_collection()

    def ensure_memory_collection(self):

        collections = self.client.get_collections().collections

        names = [c.name for c in collections]

        if MEMORY_COLLECTION not in names:

            logger.info(
                f"Creating collection '{MEMORY_COLLECTION}'..."
            )

            self.client.create_collection(
                collection_name=MEMORY_COLLECTION,
                vectors_config=VectorParams(
                    size=EMBEDDING_DIMENSIONS,
                    distance=Distance.COSINE,
                ),
            )

            logger.success("Memory collection created.")

        else:

            logger.info("Memory collection already exists.")

    def list_collections(self):

        return self.client.get_collections()


qdrant_service = QdrantService()