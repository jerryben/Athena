from loguru import logger

from backend.services.memory_service import memory_service


class ContextService:

    # ============================================================
    # MEMORY KEY DETECTION
    # ============================================================

    def _detect_memory_keys(self, prompt: str):
        """
        Detect stable memory keys that are directly relevant
        to the user's question.

        Stable-key retrieval is intentionally stronger than
        semantic similarity because these memories represent
        authoritative facts, preferences, goals and experience.

        The detector uses intent patterns rather than relying
        exclusively on exact phrases.
        """

        prompt_lower = " ".join(prompt.lower().split())

        keys = []

        # ========================================================
        # FAVORITE / PREFERRED EDITOR
        # ========================================================

        editor_terms = [
            "editor",
            "text editor",
            "code editor",
            "coding editor",
        ]

        editor_intent_terms = [
            "prefer",
            "preferred",
            "favorite",
            "favourite",
            "normally use",
            "usually use",
            "typically use",
            "chosen",
            "selected",
            "use most",
            "use regularly",
            "normally",
        ]

        has_editor = any(
            term in prompt_lower
            for term in editor_terms
        )

        has_editor_intent = any(
            term in prompt_lower
            for term in editor_intent_terms
        )

        # Direct questions about the user's editor.
        editor_usage_patterns = [
            "which editor do i use",
            "what editor do i use",
            "which text editor do i use",
            "what text editor do i use",
            "which code editor do i use",
            "what code editor do i use",
            "which editor do i use most",
            "what editor do i use most",
        ]

        has_editor_usage_question = any(
            pattern in prompt_lower
            for pattern in editor_usage_patterns
        )

        if (
            has_editor
            and (
                has_editor_intent
                or has_editor_usage_question
            )
        ):
            keys.append("favorite_editor")

        # ========================================================
        # CAREER GOAL
        # ========================================================

        career_terms = [
            "career",
            "professional",
            "job",
            "career path",
        ]

        career_intent_terms = [
            "goal",
            "working toward",
            "working towards",
            "pursuing",
            "focus",
            "focused",
            "direction",
            "becoming",
            "aiming",
        ]

        has_career = any(
            term in prompt_lower
            for term in career_terms
        )

        has_career_intent = any(
            term in prompt_lower
            for term in career_intent_terms
        )

        # Examples:
        #
        # What career am I working toward?
        # What career am I pursuing?
        # What is my career goal?
        # What am I working toward?
        # What is my professional goal?
        #
        if has_career and has_career_intent:
            keys.append("career_goal")

        # Handle questions that omit the word "career"
        # but clearly ask about the user's long-term goal.
        career_goal_patterns = [
            "what am i working toward",
            "what am i working towards",
            "what am i pursuing",
            "what am i becoming",
            "what is my goal",
            "what are my goals",
            "what is my professional goal",
            "what are my professional goals",
        ]

        if any(
            phrase in prompt_lower
            for phrase in career_goal_patterns
        ):
            keys.append("career_goal")

        # ========================================================
        # DOCKER / KUBERNETES EXPERIENCE
        # ========================================================

        infrastructure_terms = [
            "docker",
            "kubernetes",
            "k8s",
            "container",
            "containers",
            "infrastructure",
        ]

        infrastructure_intent_terms = [
            "experience",
            "experienced",
            "expert",
            "expertise",
            "use",
            "using",
            "used",
            "work",
            "worked",
            "working",
            "familiar",
            "know",
            "skills",
            "skill",
            "technologies",
            "technology",
            "proficient",
            "proficiency",
            "background",
            "comfortable",
            "knowledge",
        ]

        infrastructure_question_patterns = [
            "do i have experience",
            "am i experienced",
            "am i an expert",
            "do i know",
            "am i familiar",
            "have i used",
            "have i worked",
            "do i use",
            "what technologies do i use",
            "what infrastructure technologies do i use",
            "what container technologies do i use",
            "what am i experienced with",
        ]

        has_infrastructure = any(
            term in prompt_lower
            for term in infrastructure_terms
        )

        has_infrastructure_intent = any(
            term in prompt_lower
            for term in infrastructure_intent_terms
        )

        has_infrastructure_question = any(
            pattern in prompt_lower
            for pattern in infrastructure_question_patterns
        )

        if (
            has_infrastructure
            and (
                has_infrastructure_intent
                or has_infrastructure_question
            )
        ):
            keys.append(
                "docker_usage_kubernetes_experience"
            )

        # ========================================================
        # REMOVE DUPLICATES
        # ========================================================

        return list(dict.fromkeys(keys))

    # ============================================================
    # BUILD CONTEXT
    # ============================================================

    def build_context(self, prompt: str):

        logger.info("=" * 60)
        logger.info("BUILDING CONTEXT")
        logger.info("=" * 60)

        # ========================================================
        # 1. SEMANTIC RETRIEVAL
        # ========================================================

        memories = memory_service.search(
            query=prompt,
            limit=5,
        )

        logger.info(
            f"Semantic memories found: {memories['count']}"
        )

        semantic_results = memories.get(
            "results",
            [],
        )

        # ========================================================
        # 2. STABLE-KEY RETRIEVAL
        # ========================================================

        detected_keys = self._detect_memory_keys(prompt)

        logger.info(
            f"Detected memory keys: {detected_keys}"
        )

        keyed_results = []

        for key in detected_keys:

            try:

                point = memory_service.find_by_key(
                    key=key
                )

                if not point:

                    logger.info(
                        f"No authoritative memory found "
                        f"for key: {key}"
                    )

                    continue

                payload = point.payload or {}

                memory_text = payload.get("text")

                if not memory_text:

                    logger.warning(
                        f"Memory for key '{key}' "
                        f"has no text."
                    )

                    continue

                keyed_item = {
                    "memory": memory_text,
                    "key": payload.get("key"),
                    "type": payload.get("type"),
                    "importance": payload.get(
                        "importance",
                        5,
                    ),
                    "access_count": payload.get(
                        "access_count",
                        0,
                    ),
                    "score": 1.0,
                    "rank": 1.0,
                    "authoritative": True,
                }

                keyed_results.append(
                    keyed_item
                )

                logger.info(
                    f"Authoritative memory -> "
                    f"{memory_text} "
                    f"(key={key})"
                )

            except Exception as exc:

                logger.exception(
                    f"Stable-key retrieval failed "
                    f"for key '{key}': {exc}"
                )

        # ========================================================
        # 3. RANK SEMANTIC MEMORIES
        # ========================================================

        for item in semantic_results:

            similarity = (
                item.get("score", 0) or 0
            )

            importance = (
                item.get("importance", 5) or 5
            )

            access_count = (
                item.get("access_count", 0) or 0
            )

            usage = min(
                access_count / 20,
                1.0,
            )

            item["rank"] = (
                (similarity * 0.70)
                + ((importance / 10) * 0.20)
                + (usage * 0.10)
            )

            item["authoritative"] = False

        # ========================================================
        # 4. MERGE RESULTS
        # ========================================================

        combined = []

        # Authoritative memories first.
        combined.extend(keyed_results)

        # Semantic memories second.
        combined.extend(semantic_results)

        # ========================================================
        # 5. DEDUPLICATE
        # ========================================================

        unique = []

        seen_keys = set()
        seen_texts = set()

        for item in combined:

            key = item.get("key")

            text = item.get(
                "memory",
                "",
            ).strip()

            # Stable key is strongest identity.
            if key and key in seen_keys:

                logger.info(
                    f"Skipping duplicate keyed memory: {key}"
                )

                continue

            # Text-level duplicate protection.
            if text and text in seen_texts:

                logger.info(
                    f"Skipping duplicate memory text: {text}"
                )

                continue

            if key:
                seen_keys.add(key)

            if text:
                seen_texts.add(text)

            unique.append(item)

        # ========================================================
        # 6. SORT
        # ========================================================

        unique.sort(
            key=lambda item: (
                item.get(
                    "authoritative",
                    False,
                ),
                item.get(
                    "rank",
                    0,
                ),
            ),
            reverse=True,
        )

        # ========================================================
        # 7. SELECT MEMORIES
        # ========================================================

        context = []

        MIN_SIMILARITY = 0.70

        for item in unique:

            similarity = (
                item.get(
                    "score",
                    0,
                )
                or 0
            )

            rank = (
                item.get(
                    "rank",
                    0,
                )
                or 0
            )

            memory = item.get(
                "memory",
                "",
            )

            key = item.get(
                "key"
            )

            authoritative = item.get(
                "authoritative",
                False,
            )

            logger.info(
                f"Memory -> {memory} "
                f"(key={key}, "
                f"similarity={similarity:.3f}, "
                f"importance={item.get('importance', 5)}, "
                f"access_count={item.get('access_count', 0)}, "
                f"rank={rank:.3f}, "
                f"authoritative={authoritative})"
            )

            # ====================================================
            # AUTHORITATIVE MEMORIES
            #
            # Stable-key memories bypass semantic threshold.
            # ====================================================

            if authoritative:

                logger.info(
                    "Accepted authoritative memory."
                )

                context.append(
                    f"- {memory}"
                )

                continue

            # ====================================================
            # SEMANTIC MEMORIES
            #
            # Normal semantic memories still require threshold.
            # ====================================================

            if similarity < MIN_SIMILARITY:

                logger.info(
                    "Rejected semantic memory "
                    "(low semantic similarity)."
                )

                continue

            logger.info(
                "Accepted semantic memory."
            )

            context.append(
                f"- {memory}"
            )

        # ========================================================
        # 8. NO RELEVANT MEMORIES
        # ========================================================

        if not context:

            logger.info(
                "No memories passed relevance checks."
            )

            return ""

        # ========================================================
        # 9. BUILD FINAL CONTEXT
        # ========================================================

        logger.info(
            f"Injected {len(context)} memories into prompt."
        )

        final_context = "\n".join(
            context
        )

        logger.info(
            "Final context:"
        )

        logger.info(
            final_context
        )

        return final_context


context_service = ContextService()