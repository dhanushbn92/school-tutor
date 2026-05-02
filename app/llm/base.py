from typing import Protocol, TypeVar, TypedDict

from pydantic import BaseModel


class LLMError(Exception):
    """Raised when an LLM call fails permanently (exhausted retries or auth errors)."""


T = TypeVar("T", bound=BaseModel)


class ChatTurn(TypedDict):
    role: str  # "system" | "user" | "assistant"
    content: str


class LLMProvider(Protocol):
    def generate_structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        model: str | None = None,
        temperature: float = 0.3,
    ) -> T: ...

    def chat(
        self,
        *,
        messages: list[ChatTurn],
        model: str | None = None,
        temperature: float = 0.4,
        max_tokens: int = 800,
    ) -> str: ...
