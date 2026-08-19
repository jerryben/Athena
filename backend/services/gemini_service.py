from pathlib import Path

from google import genai
from loguru import logger

from backend.core.config import settings
from backend.services.context_service import context_service


SYSTEM_PROMPT = Path(
    "backend/prompts/system.md"
).read_text(encoding="utf-8")


class GeminiService:

    def __init__(self):

        self.client = genai.Client(
            api_key=settings.GOOGLE_API_KEY
        )

    def generate(
        self,
        prompt: str,
        history: list | None = None,
        model: str | None = None
    ):

        if model is None:
            model = settings.GEMINI_MODEL

        memory_context = context_service.build_context(prompt)

        system_instruction = SYSTEM_PROMPT

        if memory_context:

            system_instruction += (
                "\n\nRelevant long-term memories:\n"
                f"{memory_context}"
            )

        messages = []

        if history:
            messages.extend(history)

        logger.info("Sending request to Gemini...")

        response = self.client.models.generate_content(
            model=model,
            contents=messages + [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            config={
                "system_instruction": system_instruction,
                "temperature": 0.4,
            }
        )

        logger.info("Gemini responded.")

        return {
            "model": model,
            "response": response.text,
            "done": True
        }


gemini_service = GeminiService()