"""Athena AI configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "Athena AI"
    VERSION: str = "0.2.0"
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Ollama
    OLLAMA_URL: str = "http://localhost:11434"

    # LiteLLM (proxy for OpenAI-compatible API)
    LITELLM_URL: str = "http://localhost:4000"

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str = ""

    # Log
    LOG_LEVEL: str = "INFO"

    # LLM
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_API_KEY: str = "ollama"
    LLM_MODEL: str = "llama3.2:3b-instruct-q5_K_M"

    # Obsidian
    OBSIDIAN_VAULT_PATH: str = "/home/jerry/obsidian"

    # Joplin
    JOPLIN_API_URL: str = "http://localhost:41184"
    JOPLIN_API_KEY: str = ""

    # Embedding
    EMBEDDING_MODEL: str = "nomic-embed-text:latest"

    # Gemini (optional)
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-pro"

    # Voice
    VOICE_LANGUAGE: str = "en"


settings = Settings()
