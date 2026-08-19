from loguru import logger


class MemoryConsiderator:
    """
    Determines what should happen to a newly extracted memory.

    Possible operations:

        create     -> no existing memory with this key
        duplicate  -> same key and same memory
        update     -> same key but different memory
        ignore     -> invalid candidate

    Stable keys are authoritative for keyed memories.
    """

    VALID_TYPES = {
        "preference",
        "identity",
        "goal",
        "fact",
    }

    VALID_OPERATIONS = {
        "create",
        "update",
        "duplicate",
        "ignore",
    }

    def consider(
        self,
        candidate: dict,
        existing: list[dict] | None = None,
    ) -> dict:

        logger.info(
            "========== MEMORY CONSIDERATOR =========="
        )

        if not isinstance(candidate, dict):
            logger.warning("Candidate is not a dictionary.")
            return {
                "save": False,
                "operation": "ignore",
            }

        if not candidate.get("save"):
            logger.info(
                "Candidate marked as not saveable."
            )
            return {
                "save": False,
                "operation": "ignore",
            }

        memory = candidate.get("memory", "")
        if not isinstance(memory, str):
            memory = ""
        memory = memory.strip()

        memory_type = str(
            candidate.get("type", "fact")
        ).strip().lower()

        key = candidate.get("key", "")
        if not isinstance(key, str):
            key = ""
        key = key.strip().lower()

        importance = candidate.get("importance", 5)

        try:
            importance = int(importance)
        except (TypeError, ValueError):
            importance = 5

        importance = max(1, min(10, importance))

        if memory_type not in self.VALID_TYPES:
            logger.warning(
                f"Invalid memory type: {memory_type}"
            )
            return {
                "save": False,
                "operation": "ignore",
            }

        if not memory or not key:
            logger.warning(
                "Candidate is missing memory text or key."
            )
            return {
                "save": False,
                "operation": "ignore",
            }

        existing = existing or []

        logger.info(f"Candidate key: {key}")
        logger.info(f"Candidate type: {memory_type}")
        logger.info(
            f"Existing memories supplied: {len(existing)}"
        )

        # -------------------------------------------------
        # Find the existing memory with the same stable key.
        # -------------------------------------------------

        matching_memory = None

        for item in existing:
            if not isinstance(item, dict):
                continue

            existing_key = item.get("key", "")

            if not isinstance(existing_key, str):
                continue

            if existing_key.strip().lower() == key:
                matching_memory = item
                break

        # -------------------------------------------------
        # CREATE
        # -------------------------------------------------

        if matching_memory is None:
            logger.info(
                "No existing memory found with this key."
            )
            logger.success(
                f"Memory operation: CREATE ({key})"
            )

            return {
                "save": True,
                "operation": "create",
                "memory": memory,
                "type": memory_type,
                "key": key,
                "importance": importance,
            }

        # -------------------------------------------------
        # Existing memory
        # -------------------------------------------------

        existing_text = matching_memory.get(
            "memory",
            "",
        )

        if not isinstance(existing_text, str):
            existing_text = ""

        existing_text = existing_text.strip()

        existing_point_id = matching_memory.get("id")
        existing_type = matching_memory.get("type")

        logger.info(
            f"Existing memory: {existing_text}"
        )
        logger.info(
            f"Existing memory type: {existing_type}"
        )
        logger.info(
            f"Existing point ID: {existing_point_id}"
        )

        # -------------------------------------------------
        # DUPLICATE
        # -------------------------------------------------

        if existing_text.casefold() == memory.casefold():
            logger.info(
                "Candidate is identical to existing memory."
            )
            logger.info(
                f"Memory operation: DUPLICATE ({key})"
            )

            return {
                "save": False,
                "operation": "duplicate",
                "memory": memory,
                "type": memory_type,
                "key": key,
                "importance": importance,
                "existing_memory": existing_text,
                "existing_point_id": existing_point_id,
            }

        # -------------------------------------------------
        # UPDATE
        # -------------------------------------------------

        logger.info(
            "Same memory key exists with different content."
        )
        logger.warning(
            f"Previous memory: {existing_text}"
        )
        logger.info(
            f"New memory: {memory}"
        )
        logger.success(
            f"Memory operation: UPDATE ({key})"
        )

        return {
            "save": True,
            "operation": "update",
            "memory": memory,
            "type": memory_type,
            "key": key,
            "importance": importance,
            "previous_memory": existing_text,
            "previous_point_id": existing_point_id,
        }


memory_considerator = MemoryConsiderator()
