from pathlib import Path

from openai import OpenAI
from loguru import logger

from backend.core.config import settings


# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = Path(
    "backend/prompts/system.md"
).read_text(encoding="utf-8")


# ============================================================
# LLM SERVICE
# ============================================================

class LLMService:

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_BASE_URL,
        )

        logger.info(
            "LLMService initialized | model={} | base_url={}",
            settings.LLM_MODEL,
            settings.LLM_BASE_URL,
        )

    def generate(
        self,
        prompt: str,
        history: list | None = None,
        context: str = "",
    ):

        if history is None:
            history = []

        # ====================================================
        # BUILD SYSTEM PROMPT
        # ====================================================

        system_prompt = SYSTEM_PROMPT

        if context:
            system_prompt += (
                "\n\nRelevant long-term memories:\n"
                + context
            )

        # ====================================================
        # BUILD MESSAGE LIST
        # ====================================================

        messages = [
            {
                "role": "system",
                "content": system_prompt,
            }
        ]

        messages.extend(history)

        messages.append(
            {
                "role": "user",
                "content": prompt,
            }
        )

        # ====================================================
        # DEBUG / DIAGNOSTICS
        # ====================================================

        logger.info(
            "LLM request | model={} | history_length={} | memory_context={}",
            settings.LLM_MODEL,
            len(history),
            bool(context),
        )

        logger.info(
            "Client exists: {}",
            hasattr(self, "client"),
        )

        logger.info(
            "Memory context:\n{}",
            context,
        )

        logger.info(
            "Messages:\n{}",
            messages,
        )

        # ====================================================
        # CALL LLM
        # ====================================================

        response = self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            temperature=0.4,
        )

        # ====================================================
        # RESPONSE
        # ====================================================

        result = response.choices[0].message.content

        logger.info(
            "LLM response received | model={} | response_length={}",
            settings.LLM_MODEL,
            len(result or ""),
        )

        return {
            "model": settings.LLM_MODEL,
            "response": result,
            "done": True,
        }


# ============================================================
# SINGLETON
# ============================================================

llm_service = LLMService()
