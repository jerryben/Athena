from datetime import datetime
from uuid import uuid4

from loguru import logger
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
)

from backend.core.constants import MEMORY_COLLECTION
from backend.services.embedding_service import embedding_service
from backend.services.qdrant_service import qdrant_service


class MemoryService:

    # =====================================================
    # INTERNAL SEMANTIC SEARCH
    # =====================================================

    def _search_points(
        self,
        query: str,
        limit: int = 5,
        memory_type: str | None = None,
        memory_key: str | None = None,
        track_usage: bool = True,
    ):
        logger.info(
            f"Searching memory collection: {MEMORY_COLLECTION}"
        )

        vector = embedding_service.embed(query)

        kwargs = {
            "collection_name": MEMORY_COLLECTION,
            "query_vector": vector,
            "limit": limit,
        }

        filters = []

        if memory_type:
            filters.append(
                FieldCondition(
                    key="type",
                    match=MatchValue(value=memory_type),
                )
            )

        if memory_key:
            filters.append(
                FieldCondition(
                    key="key",
                    match=MatchValue(value=memory_key),
                )
            )

        if filters:
            kwargs["query_filter"] = Filter(must=filters)

        results = qdrant_service.client.search(**kwargs)

        logger.info(
            f"Found {len(results)} similar memories"
        )

        if track_usage:
            now = datetime.utcnow().isoformat()

            for point in results:
                access_count = (
                    point.payload.get("access_count", 0) + 1
                )

                qdrant_service.client.set_payload(
                    collection_name=MEMORY_COLLECTION,
                    payload={
                        "access_count": access_count,
                        "last_accessed": now,
                    },
                    points=[point.id],
                )

        return results

    # =====================================================
    # FIND MEMORY BY STABLE KEY
    # =====================================================

    def find_by_key(
        self,
        key: str,
        memory_type: str | None = None,
    ):
        key = str(key).strip().lower()

        if not key:
            return None

        logger.info(
            f"Looking for memory by key: {key}"
        )

        filters = [
            FieldCondition(
                key="key",
                match=MatchValue(value=key),
            )
        ]

        if memory_type:
            filters.append(
                FieldCondition(
                    key="type",
                    match=MatchValue(value=memory_type),
                )
            )

        result = qdrant_service.client.scroll(
            collection_name=MEMORY_COLLECTION,
            scroll_filter=Filter(must=filters),
            limit=1,
            with_payload=True,
            with_vectors=False,
        )

        points = result[0]

        if not points:
            logger.info(
                f"No memory found for key: {key}"
            )
            return None

        point = points[0]

        logger.info(
            f"Memory found for key '{key}': "
            f"{point.payload.get('text')}"
        )

        return point

    # =====================================================
    # CREATE MEMORY
    # =====================================================

    def create_memory(
        self,
        text: str,
        memory_type: str,
        key: str | None,
        importance: int = 5,
    ):
        logger.info("Creating new memory...")

        vector = embedding_service.embed(text)

        now = datetime.utcnow().isoformat()

        normalized_key = (
            key.strip().lower()
            if isinstance(key, str) and key.strip()
            else None
        )

        payload = {
            "text": text,
            "type": memory_type,
            "key": normalized_key,
            "importance": importance,
            "access_count": 0,
            "last_accessed": now,
            "created_at": now,
        }

        point = PointStruct(
            id=str(uuid4()),
            vector=vector,
            payload=payload,
        )

        qdrant_service.client.upsert(
            collection_name=MEMORY_COLLECTION,
            points=[point],
        )

        logger.success(
            "New memory created successfully."
        )

        logger.info(
            f"Memory Count: {self.count()}"
        )

        return True

    # =====================================================
    # UPDATE MEMORY BY KEY
    # =====================================================

    def update_by_key(
        self,
        key: str,
        text: str,
        memory_type: str,
        importance: int = 5,
    ):
        key = str(key).strip().lower()

        logger.info(
            f"Updating memory with key: {key}"
        )

        existing = self.find_by_key(
            key=key,
            memory_type=memory_type,
        )

        if not existing:
            logger.warning(
                f"Cannot update memory. "
                f"No memory exists for key: {key}"
            )
            return False

        now = datetime.utcnow().isoformat()

        created_at = existing.payload.get(
            "created_at",
            now,
        )

        access_count = existing.payload.get(
            "access_count",
            0,
        )

        vector = embedding_service.embed(text)

        updated_payload = {
            "text": text,
            "type": memory_type,
            "key": key,
            "importance": importance,
            "access_count": access_count,
            "last_accessed": now,
            "created_at": created_at,
        }

        updated_point = PointStruct(
            id=existing.id,
            vector=vector,
            payload=updated_payload,
        )

        qdrant_service.client.upsert(
            collection_name=MEMORY_COLLECTION,
            points=[updated_point],
        )

        logger.success(
            f"Memory updated successfully: {key}"
        )

        return "updated"

    # =====================================================
    # SAVE MEMORY
    # =====================================================

    def save(
        self,
        text: str,
        metadata: dict | None = None,
    ):
        logger.info(
            "========== SAVE() CALLED =========="
        )

        metadata = metadata or {}

        memory_type = metadata.get(
            "type",
            "fact",
        )

        memory_key = metadata.get("key")
        importance = metadata.get("importance", 5)
        operation = (
            str(
                metadata.get(
                    "operation",
                    "create",
                )
            )
            .strip()
            .lower()
        )

        if isinstance(memory_key, str):
            memory_key = memory_key.strip().lower()

        try:
            importance = int(importance)
        except (TypeError, ValueError):
            importance = 5

        importance = max(1, min(10, importance))

        logger.info(f"Memory type: {memory_type}")
        logger.info(f"Memory key: {memory_key}")
        logger.info(f"Importance: {importance}")
        logger.info(f"Requested operation: {operation}")

        # =================================================
        # KEY-BASED MEMORY
        # =================================================

        if memory_key:
            existing = self.find_by_key(
                key=memory_key,
                memory_type=memory_type,
            )

            if not existing:
                if operation == "update":
                    logger.warning(
                        "UPDATE requested but no existing memory "
                        "was found. Creating memory instead."
                    )

                return self.create_memory(
                    text=text,
                    memory_type=memory_type,
                    key=memory_key,
                    importance=importance,
                )

            existing_text = existing.payload.get(
                "text",
                "",
            )

            logger.info(
                f"Existing memory: {existing_text}"
            )

            if (
                isinstance(existing_text, str)
                and existing_text.strip().casefold()
                == text.strip().casefold()
            ):
                logger.info(
                    "Exact memory already exists."
                )
                return False

            if operation == "update":
                return self.update_by_key(
                    key=memory_key,
                    text=text,
                    memory_type=memory_type,
                    importance=importance,
                )

            logger.warning(
                "Memory conflict detected."
            )
            logger.warning(
                f"Existing: {existing_text}"
            )
            logger.warning(
                f"Incoming: {text}"
            )
            logger.warning(
                "Memory was NOT overwritten."
            )

            return False

        # =================================================
        # UNKEYED MEMORY
        # =================================================

        logger.info("No memory key supplied.")
        logger.info("Checking semantic similarity...")

        existing = self._search_points(
            query=text,
            limit=1,
            memory_type=memory_type,
            track_usage=False,
        )

        if existing.points:
            best_match = existing.points[0]
            similarity = best_match.score or 0

            logger.info(
                f"Best similarity score: {similarity}"
            )

            existing_text = best_match.payload.get(
                "text",
                "",
            )

            logger.info(
                f"Existing memory: {existing_text}"
            )

            if similarity >= 0.95:
                logger.info(
                    "Semantic duplicate detected."
                )
                return False

        return self.create_memory(
            text=text,
            memory_type=memory_type,
            key=None,
            importance=importance,
        )

    # =====================================================
    # MEMORY TYPE WRAPPERS
    # =====================================================

    def save_fact(
        self,
        text: str,
        importance: int = 5,
        key: str | None = None,
        operation: str = "create",
    ):
        return self.save(
            text=text,
            metadata={
                "type": "fact",
                "key": key,
                "importance": importance,
                "operation": operation,
            },
        )

    def save_preference(
        self,
        text: str,
        importance: int = 5,
        key: str | None = None,
        operation: str = "create",
    ):
        return self.save(
            text=text,
            metadata={
                "type": "preference",
                "key": key,
                "importance": importance,
                "operation": operation,
            },
        )

    def save_identity(
        self,
        text: str,
        importance: int = 5,
        key: str | None = None,
        operation: str = "create",
    ):
        return self.save(
            text=text,
            metadata={
                "type": "identity",
                "key": key,
                "importance": importance,
                "operation": operation,
            },
        )

    def save_goal(
        self,
        text: str,
        importance: int = 5,
        key: str | None = None,
        operation: str = "create",
    ):
        return self.save(
            text=text,
            metadata={
                "type": "goal",
                "key": key,
                "importance": importance,
                "operation": operation,
            },
        )

    # =====================================================
    # COUNT
    # =====================================================

    def count(self):
        result = qdrant_service.client.count(
            collection_name=MEMORY_COLLECTION,
            exact=True,
        )
        return result.count

    # =====================================================
    # SEARCH
    # =====================================================

    def search(
        self,
        query: str,
        limit: int = 5,
        memory_type: str | None = None,
        memory_key: str | None = None,
    ):
        logger.info(
            f"Searching memories for: '{query}'"
        )

        results = self._search_points(
            query=query,
            limit=limit,
            memory_type=memory_type,
            memory_key=memory_key,
        )

        logger.info(
            f"Returning {len(results)} memories"
        )

        return {
            "count": len(results),
            "results": [
                {
                    "id": str(p.id),
                    "memory": p.payload.get("text", ""),
                    "type": p.payload.get("type"),
                    "key": p.payload.get("key"),
                    "importance": p.payload.get(
                        "importance",
                        5,
                    ),
                    "access_count": p.payload.get(
                        "access_count",
                        0,
                    ),
                    "last_accessed": p.payload.get(
                        "last_accessed"
                    ),
                    "created_at": p.payload.get(
                        "created_at"
                    ),
                    "score": p.score,
                }
                for p in results
            ],
        }

    # =====================================================
    # CLEAR
    # =====================================================

    def clear(self):
        logger.info("Clearing all memories...")

        qdrant_service.client.delete_collection(
            collection_name=MEMORY_COLLECTION
        )

        qdrant_service.ensure_memory_collection()

        logger.info(
            "Memory collection recreated."
        )

        return {
            "status": "Memory cleared"
        }


memory_service = MemoryService()
