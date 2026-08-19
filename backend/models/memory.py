from pydantic import BaseModel


class MemoryDecision(BaseModel):

    save: bool

    memory: str | None = None

    category: str = "fact"

    importance: int = 5

    confidence: float = 1.0