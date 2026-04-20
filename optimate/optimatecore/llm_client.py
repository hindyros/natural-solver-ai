"""Provider-agnostic LLM client abstraction.

All agents call `LLMClient.complete()` — the underlying provider is
swapped by instantiating a different subclass. This keeps every agent
free of provider-specific SDK imports.

Supported providers:
    - anthropic  (default)  — claude-* models via Anthropic SDK
    - openai                — gpt-* models via OpenAI SDK
    - groq                  — llama-*/mixtral-* models via Groq SDK (openai-compatible)
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Literal

from optimatecore.exceptions import ProviderError, RateLimitError

logger = logging.getLogger(__name__)

Provider = Literal["anthropic", "openai", "groq"]


@dataclass
class UsageStats:
    """Accumulated token usage across all LLM calls for a run."""

    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_calls: int = 0

    def update(self, input_tokens: int, output_tokens: int) -> None:
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_calls += 1

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    def __str__(self) -> str:
        return (
            f"{self.total_calls} calls | "
            f"{self.total_input_tokens:,} in + {self.total_output_tokens:,} out "
            f"= {self.total_tokens:,} total tokens"
        )


class LLMClient(ABC):
    """Minimal async interface used by every agent."""

    def __init__(self) -> None:
        self.usage = UsageStats()

    @abstractmethod
    async def complete(
        self,
        *,
        system: str,
        user: str,
        model: str,
        max_tokens: int,
    ) -> str:
        """Return the assistant text response and update self.usage."""


class AnthropicLLMClient(LLMClient):
    def __init__(self, api_key: str):
        super().__init__()
        from anthropic import AsyncAnthropic
        self._client = AsyncAnthropic(api_key=api_key)
        self._provider = "anthropic"

    async def complete(self, *, system: str, user: str, model: str, max_tokens: int) -> str:
        import anthropic as _anthropic

        try:
            response = await self._client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=[{"role": "user", "content": user}],
            )
        except _anthropic.RateLimitError as e:
            raise RateLimitError(self._provider) from e
        except (_anthropic.APIConnectionError, _anthropic.InternalServerError) as e:
            raise ProviderError(self._provider, str(e)) from e

        self.usage.update(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
        return response.content[0].text


class OpenAILLMClient(LLMClient):
    def __init__(self, api_key: str, base_url: str | None = None):
        super().__init__()
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._provider = "openai"

    async def complete(self, *, system: str, user: str, model: str, max_tokens: int) -> str:
        import openai as _openai

        try:
            response = await self._client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except _openai.RateLimitError as e:
            raise RateLimitError(self._provider) from e
        except (_openai.APIConnectionError, _openai.InternalServerError) as e:
            raise ProviderError(self._provider, str(e)) from e

        usage = response.usage
        if usage:
            self.usage.update(
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
            )
        return response.choices[0].message.content or ""


class GroqLLMClient(LLMClient):
    def __init__(self, api_key: str):
        super().__init__()
        from groq import AsyncGroq
        self._client = AsyncGroq(api_key=api_key)
        self._provider = "groq"

    async def complete(self, *, system: str, user: str, model: str, max_tokens: int) -> str:
        import groq as _groq

        try:
            response = await self._client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            )
        except _groq.RateLimitError as e:
            raise RateLimitError(self._provider) from e
        except (_groq.APIConnectionError, _groq.InternalServerError) as e:
            raise ProviderError(self._provider, str(e)) from e

        usage = response.usage
        if usage:
            self.usage.update(
                input_tokens=usage.prompt_tokens,
                output_tokens=usage.completion_tokens,
            )
        return response.choices[0].message.content or ""


def build_client(provider: Provider, **kwargs) -> LLMClient:
    """Factory — builds the right client from a provider name + credentials."""
    if provider == "anthropic":
        return AnthropicLLMClient(api_key=kwargs["api_key"])
    if provider == "openai":
        return OpenAILLMClient(
            api_key=kwargs["api_key"],
            base_url=kwargs.get("base_url"),
        )
    if provider == "groq":
        return GroqLLMClient(api_key=kwargs["api_key"])
    raise ValueError(f"Unknown provider: {provider!r}. Choose from: anthropic, openai, groq")
