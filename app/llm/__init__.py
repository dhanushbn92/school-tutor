import os
from functools import lru_cache

from app.core.config import get_settings
from app.llm.anthropic_provider import AnthropicProvider
from app.llm.base import LLMError, LLMProvider
from app.llm.openai_compat import OpenAICompatProvider
from app.llm.stub_provider import StubProvider


@lru_cache
def get_llm_provider() -> LLMProvider:
    settings = get_settings()
    provider = settings.llm_provider.lower()
    if provider == "anthropic":
        # Allow ANTHROPIC_API_KEY to come from the environment even if the
        # user didn't add it to .env (common dev setup — key already exported
        # in the shell). Falling back to os.environ keeps the bootstrap path
        # frictionless.
        api_key = settings.anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMError(
                "LLM_PROVIDER=anthropic but ANTHROPIC_API_KEY is not set "
                "(neither in .env nor in the environment)"
            )
        return AnthropicProvider(
            api_key=api_key,
            default_model=settings.llm_model or settings.anthropic_default_model,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    if provider == "groq":
        if not settings.groq_api_key:
            raise LLMError("LLM_PROVIDER=groq but GROQ_API_KEY is not set in .env")
        return OpenAICompatProvider(
            api_key=settings.groq_api_key,
            base_url=settings.groq_base_url,
            default_model=settings.llm_model or settings.groq_default_model,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    if provider == "openai":
        if not settings.openai_api_key:
            raise LLMError("LLM_PROVIDER=openai but OPENAI_API_KEY is not set in .env")
        return OpenAICompatProvider(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            default_model=settings.llm_model or settings.openai_default_model,
            timeout=settings.llm_timeout_seconds,
            max_retries=settings.llm_max_retries,
        )
    if provider == "stub":
        return StubProvider()
    raise LLMError(f"Unknown LLM_PROVIDER={settings.llm_provider!r}")


__all__ = ["LLMError", "LLMProvider", "get_llm_provider"]
