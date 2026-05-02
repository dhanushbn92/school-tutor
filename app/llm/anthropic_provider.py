"""Anthropic (Claude) provider implementing the LLMProvider Protocol.

We use the official `anthropic` Python SDK. Anthropic's Messages API does
not have OpenAI's `response_format={"type": "json_object"}` mode, so for
structured output we:
  1. Inject the JSON Schema of the response model into the system prompt.
  2. Tell Claude to emit JSON only.
  3. Strip ```json ... ``` fences if Claude wraps the output despite
     instructions (it sometimes does, especially on long responses).
  4. Retry on validation errors with the validation message fed back as
     a follow-up user turn — same retry pattern as `OpenAICompatProvider`.

The `chat()` method is a plain pass-through to `messages.create` with the
`system` turn split out of the message list (Anthropic takes `system` as
a top-level kwarg, not as a message role).
"""

from __future__ import annotations

import json
from typing import TypeVar

import anthropic
from pydantic import BaseModel, ValidationError

from app.llm.base import ChatTurn, LLMError


T = TypeVar("T", bound=BaseModel)


def _strip_json_fences(text: str) -> str:
    """Claude sometimes wraps JSON in ```json ... ``` fences. Strip them.

    Mirrors the logic in scripts/extract_topic_texts.py.
    """
    s = text.strip()
    if s.startswith("```"):
        # Drop the leading ``` (and optional language tag) and trailing ```.
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:]
        s = s.strip()
        # If there's a trailing fence we already stripped via .strip("`")
        # above, but in case Claude added trailing whitespace inside the
        # fence, normalise once more.
        s = s.strip("`").strip()
    return s


def _split_system(messages: list[ChatTurn]) -> tuple[str | None, list[dict[str, str]]]:
    """Anthropic's API takes `system` as a top-level kwarg, not a role.

    Pull any `system` turns out of the list, concatenate them, and return
    the remaining (user/assistant) turns.
    """
    system_chunks: list[str] = []
    rest: list[dict[str, str]] = []
    for m in messages:
        if m["role"] == "system":
            system_chunks.append(m["content"])
        else:
            rest.append({"role": m["role"], "content": m["content"]})
    system_text = "\n\n".join(system_chunks) if system_chunks else None
    return system_text, rest


class AnthropicProvider:
    """LLM provider backed by Claude via the Anthropic Messages API."""

    def __init__(
        self,
        *,
        api_key: str,
        default_model: str,
        timeout: int = 120,
        max_retries: int = 2,
        max_tokens_structured: int = 8000,
    ):
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout)
        self._default_model = default_model
        self._max_retries = max_retries
        self._max_tokens_structured = max_tokens_structured

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
        system_prompt = (
            f"{system}\n\n"
            "Respond ONLY with valid JSON matching this JSON Schema. "
            "Do NOT wrap the JSON in markdown code fences.\n"
            f"{schema_hint}"
        )
        # Anthropic doesn't have a JSON mode; we keep our own retry loop
        # that feeds validation errors back to the model.
        messages: list[dict[str, str]] = [{"role": "user", "content": user}]

        last_error: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._client.messages.create(
                    model=model_name,
                    max_tokens=self._max_tokens_structured,
                    temperature=temperature,
                    system=system_prompt,
                    messages=messages,
                )
            except anthropic.APIError as exc:
                raise LLMError(f"Anthropic API error: {exc}") from exc

            content = "".join(
                block.text
                for block in response.content
                if getattr(block, "type", None) == "text"
            )
            cleaned = _strip_json_fences(content)
            try:
                data = json.loads(cleaned)
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
                            "Return ONLY valid JSON matching the schema, no prose, "
                            "no markdown fences."
                        ),
                    }
                )

        raise LLMError(
            f"Failed to produce valid structured output after "
            f"{self._max_retries + 1} attempts: {last_error}"
        )

    def chat(
        self,
        *,
        messages: list[ChatTurn],
        model: str | None = None,
        temperature: float = 0.4,
        max_tokens: int = 800,
    ) -> str:
        model_name = model or self._default_model
        system_text, rest = _split_system(messages)
        kwargs: dict = {
            "model": model_name,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": rest,
        }
        if system_text is not None:
            kwargs["system"] = system_text
        try:
            response = self._client.messages.create(**kwargs)
        except anthropic.APIError as exc:
            raise LLMError(f"Anthropic API error: {exc}") from exc
        text = "".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        )
        return text.strip()
