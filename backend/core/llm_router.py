from backend.services.ollama_service import llm_service


class LLMRouter:

    def generate(
        self,
        prompt: str,
        history: list,
        context: str = "",
    ):

        return llm_service.generate(
            prompt,
            history,
            context,
        )


llm_router = LLMRouter()