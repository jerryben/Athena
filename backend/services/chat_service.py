from loguru import logger

from backend.core.llm_router import llm_router
from backend.services.history_service import history_service
from backend.services.memory_service import memory_service
from backend.services.memory_intelligence import memory_intelligence
from backend.services.context_service import context_service
from backend.services.memory_considerator import memory_considerator


logger.info("CHAT SERVICE LOADED")


class ChatService:

    def chat(self, prompt: str):

        logger.info("=" * 70)
        logger.info("NEW CHAT REQUEST")
        logger.info(f"Prompt: {prompt}")

        # -------------------------------------------------------
        # Build memory context
        # -------------------------------------------------------

        logger.info("Building memory context...")

        context = context_service.build_context(prompt)

        logger.info(f"Memory Context:\n{context}")

        # -------------------------------------------------------
        # Load conversation history
        # -------------------------------------------------------

        history = history_service.messages()

        logger.info(
            f"Conversation History: {len(history)} messages"
        )

        # -------------------------------------------------------
        # Generate response
        # -------------------------------------------------------

        logger.info("Calling LLM...")

        response = llm_router.generate(
            prompt,
            history,
            context,
        )

        logger.info("LLM Response Generated")

        # -------------------------------------------------------
        # Save conversation into short-term memory
        # -------------------------------------------------------

        history_service.add("user", prompt)
        history_service.add("assistant", response["response"])

        logger.info(
            f"History Size: {len(history_service.messages())}"
        )

        # =======================================================
        # LONG-TERM MEMORY PIPELINE
        # =======================================================

        logger.info("Running Memory Intelligence...")

        candidate = memory_intelligence.should_save(prompt)

        logger.info(
            f"Memory Intelligence Result: {candidate}"
        )

        if not candidate.get("save"):
            logger.info(
                "Memory Intelligence rejected candidate."
            )
            logger.info("=" * 70)
            return response

        # -------------------------------------------------------
        # Extract candidate
        # -------------------------------------------------------

        memory_text = candidate.get("memory", "").strip()
        memory_type = candidate.get("type", "fact")
        memory_key = candidate.get("key", "").strip().lower()
        importance = candidate.get("importance", 5)

        logger.info(f"Candidate memory: {memory_text}")
        logger.info(f"Candidate type: {memory_type}")
        logger.info(f"Candidate key: {memory_key}")
        logger.info(f"Candidate importance: {importance}")

        if not memory_text or not memory_key:
            logger.warning(
                "Candidate rejected: missing memory text or stable key."
            )
            logger.info("=" * 70)
            return response

        # -------------------------------------------------------
        # Find existing memory by stable key.
        #
        # This is deliberately key-based. Do not use semantic
        # similarity to decide whether a keyed memory is the
        # same memory.
        # -------------------------------------------------------

        logger.info(
            "Searching for existing memory with the same key..."
        )

        existing_point = memory_service.find_by_key(
            key=memory_key,
            memory_type=memory_type,
        )

        existing_memories = []

        if existing_point:
            existing_memories.append(
                {
                    "id": str(existing_point.id),
                    "memory": existing_point.payload.get("text", ""),
                    "type": existing_point.payload.get("type"),
                    "key": existing_point.payload.get("key"),
                    "importance": existing_point.payload.get(
                        "importance",
                        5,
                    ),
                    "created_at": existing_point.payload.get("created_at"),
                    "last_accessed": existing_point.payload.get(
                        "last_accessed"
                    ),
                    "access_count": existing_point.payload.get(
                        "access_count",
                        0,
                    ),
                }
            )

        logger.info(
            f"Existing memories with key "
            f"'{memory_key}': {len(existing_memories)}"
        )

        # -------------------------------------------------------
        # Let MemoryConsiderator determine the operation.
        # -------------------------------------------------------

        logger.info("Running Memory Considerator...")

        decision = memory_considerator.consider(
            candidate=candidate,
            existing=existing_memories,
        )

        logger.info(
            f"Memory Considerator Result: {decision}"
        )

        operation = (
            decision.get("operation", "ignore")
            .strip()
            .lower()
        )

        logger.info(
            f"Memory operation: {operation.upper()}"
        )

        if operation == "ignore":
            logger.info("Memory candidate ignored.")
            logger.info("=" * 70)
            return response

        if operation == "duplicate":
            logger.info("Memory already exists.")
            logger.info("No database operation required.")
            logger.info("=" * 70)
            return response

        if operation not in {"create", "update"}:
            logger.warning(
                f"Unknown memory operation: {operation}"
            )
            logger.info("=" * 70)
            return response

        # -------------------------------------------------------
        # Persist memory.
        #
        # IMPORTANT:
        # The operation decided by MemoryConsiderator is passed
        # explicitly into MemoryService.
        # -------------------------------------------------------

        logger.info(
            f"Executing memory operation: {operation.upper()}"
        )

        save_kwargs = {
            "text": memory_text,
            "key": memory_key,
            "importance": importance,
            "operation": operation,
        }

        if memory_type == "preference":
            saved = memory_service.save_preference(**save_kwargs)
        elif memory_type == "goal":
            saved = memory_service.save_goal(**save_kwargs)
        elif memory_type == "identity":
            saved = memory_service.save_identity(**save_kwargs)
        else:
            saved = memory_service.save_fact(**save_kwargs)

        # -------------------------------------------------------
        # Handle MemoryService result
        # -------------------------------------------------------

        if saved is True:
            logger.success(
                "New memory saved successfully."
            )
        elif saved == "updated":
            logger.success(
                "Existing memory updated successfully."
            )
        else:
            logger.warning(
                "MemoryService did not change the database."
            )

        logger.info(
            f"Memory Count: {memory_service.count()}"
        )

        logger.info("=" * 70)

        return response


chat_service = ChatService()
