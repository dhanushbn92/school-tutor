from typing import Any, TypeVar

from pydantic import BaseModel

from app.llm.base import ChatTurn, LLMError


T = TypeVar("T", bound=BaseModel)


class StubProvider:
    """Returns canned fixtures keyed by response model class name.

    Useful for offline dev, unit tests, and skipping LLM calls in CI.
    Register fixtures at construction time; unknown models raise LLMError
    so you never silently return fake data in prod.
    """

    def __init__(self, fixtures: dict[str, dict[str, Any]] | None = None):
        self._fixtures = fixtures or {}

    def register(self, response_model: type[BaseModel], payload: dict[str, Any]) -> None:
        self._fixtures[response_model.__name__] = payload

    def generate_structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        model: str | None = None,
        temperature: float = 0.3,
    ) -> T:
        key = response_model.__name__
        if key not in self._fixtures:
            raise LLMError(
                f"StubProvider has no fixture for {key}. "
                "Switch LLM_PROVIDER to a real provider or register a fixture."
            )
        return response_model.model_validate(self._fixtures[key])

    def chat(
        self,
        *,
        messages: list[ChatTurn],
        model: str | None = None,
        temperature: float = 0.4,
        max_tokens: int = 800,
    ) -> str:
        # Stub returns the last user message reflected back so unit tests
        # can assert behaviour without an LLM. Swap in a real provider when
        # you actually want a response.
        last_user = next(
            (m for m in reversed(messages) if m.get("role") == "user"),
            None,
        )
        echo = last_user["content"] if last_user else ""
        return f"(stub) {echo[:200]}"
