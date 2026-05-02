import json
from typing import TypeVar

from openai import APIError, OpenAI
from pydantic import BaseModel, ValidationError

from app.llm.base import ChatTurn, LLMError


T = TypeVar("T", bound=BaseModel)


class OpenAICompatProvider:
    """Provider that speaks the OpenAI Chat Completions API.

    Works with OpenAI itself and any compatible endpoint such as Groq,
    Together, Anyscale, etc. Configure via base_url + api_key.
    """

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        default_model: str,
        timeout: int = 120,
        max_retries: int = 2,
    ):
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
        self._default_model = default_model
        self._max_retries = max_retries

    def generate_structured(
        self,
        *,
        system: str,
        user: str,
        response_model: type[T],
        model: str | None = None,
        temperature: float = 0.3,
    ) -> T:
        model_name = model or self._default_model
        schema_hint = json.dumps(response_model.model_json_schema(), indent=2)
        messages: list[dict[str, str]] = [
            {
                "role": "system",
                "content": (
                    f"{system}\n\n"
                    "Respond ONLY with valid JSON matching this JSON Schema:\n"
                    f"{schema_hint}"
                ),
            },
            {"role": "user", "content": user},
        ]

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    response_format={"type": "json_object"},
                    temperature=temperature,
                )
            except APIError as exc:
                raise LLMError(f"Provider API error: {exc}") from exc

            content = response.choices[0].message.content or ""
            try:
                data = json.loads(content)
                return response_model.model_validate(data)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_error = exc
                if attempt >= self._max_retries:
                    break
                messages.append({"role": "assistant", "content": content})
                messages.append(
                    {
                        "role": "user",
                        "content": (
                            f"Your previous response failed validation: {exc}. "
                            "Return ONLY valid JSON matching the schema, no prose."
                        ),
                    }
                )

        raise LLMError(
            f"Failed to produce valid structured output after {self._max_retries + 1} attempts: {last_error}"
        )

    def chat(
        self,
        *,
        messages: list[ChatTurn],
        model: str | None = None,
        temperature: float = 0.4,
        max_tokens: int = 800,
    ) -> str:
        """Plain-text chat completion. Used by the AI tutor.

        Caller is responsible for assembling the message list (system + prior
        turns + new user message). No JSON formatting is applied.
        """
        model_name = model or self._default_model
        try:
            response = self._client.chat.completions.create(
                model=model_name,
                messages=[dict(m) for m in messages],
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except APIError as exc:
            raise LLMError(f"Provider API error: {exc}") from exc
        return (response.choices[0].message.content or "").strip()
