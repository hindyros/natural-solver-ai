import asyncio
import json
import logging
import re
from typing import TypeVar, Type

from pydantic import BaseModel, ValidationError

from optimatecore.artifact_store import ArtifactStore
from optimatecore.config import (
    LIGHT_MODEL,
    LLM_MAX_TOKENS,
    MAX_LLM_RETRIES,
    RATE_LIMIT_BASE_DELAY,
    RATE_LIMIT_MAX_DELAY,
    RATE_LIMIT_MAX_RETRIES,
)
from optimatecore.exceptions import AgentError, ProviderError, RateLimitError
from optimatecore.llm_client import LLMClient

T = TypeVar("T", bound=BaseModel)


class BaseAgent:
    """Base class for all pipeline agents.

    Subclasses must implement ``run()`` with their specific typed signature.
    All LLM calls go through ``_call_llm`` (structured output) or
    ``_call_llm_text`` (free-form text), both of which handle:
      - JSON parse errors → retry with error feedback (up to MAX_LLM_RETRIES)
      - Rate-limit errors → exponential backoff (up to RATE_LIMIT_MAX_RETRIES)
      - Transient provider errors → immediate retry once
    """

    agent_name: str = "BaseAgent"
    model: str = LIGHT_MODEL
    system_prompt: str = "You are a helpful AI assistant."

    # Subclasses can set this to a cached JSON schema string to avoid
    # recomputing it on every call.
    _schema_cache: dict[type, str] = {}

    def __init__(self, client: LLMClient, store: ArtifactStore) -> None:
        self.client = client
        self.store = store
        self.logger = logging.getLogger(
            f"{self.__class__.__module__}.{self.__class__.__name__}"
        )

    async def _call_llm(
        self,
        user_prompt: str,
        output_schema: Type[T],
        max_retries: int = MAX_LLM_RETRIES,
    ) -> T:
        """Call the LLM and parse the response into a Pydantic model.

        Retries on parse failure (appending the error to the next prompt).
        Rate-limit errors use exponential backoff independently.
        """
        last_error: str | None = None
        last_response: str = ""

        for attempt in range(max_retries):
            prompt = user_prompt
            if last_error:
                prompt += (
                    f"\n\n---\nYOUR PREVIOUS RESPONSE COULD NOT BE PARSED.\n"
                    f"Error: {last_error}\n"
                    f"Please respond with ONLY valid JSON that matches the required schema."
                )

            last_response = await self._complete_with_backoff(prompt)

            try:
                parsed = self._extract_json(last_response)
                return output_schema(**parsed)
            except (json.JSONDecodeError, ValidationError, KeyError) as e:
                last_error = str(e)
                self.logger.debug(
                    "Parse attempt %d/%d failed for %s: %s",
                    attempt + 1,
                    max_retries,
                    output_schema.__name__,
                    last_error[:200],
                )

        raise AgentError(self.agent_name, last_response, last_error or "unknown")

    async def _call_llm_text(self, user_prompt: str) -> str:
        """Call the LLM and return the raw text response."""
        return await self._complete_with_backoff(user_prompt)

    async def _complete_with_backoff(self, user_prompt: str) -> str:
        """Wrap client.complete() with exponential backoff for rate limits."""
        delay = RATE_LIMIT_BASE_DELAY
        for attempt in range(RATE_LIMIT_MAX_RETRIES):
            try:
                return await self.client.complete(
                    system=self.system_prompt,
                    user=user_prompt,
                    model=self.model,
                    max_tokens=LLM_MAX_TOKENS,
                )
            except RateLimitError as e:
                if attempt >= RATE_LIMIT_MAX_RETRIES - 1:
                    raise
                wait = min(delay, RATE_LIMIT_MAX_DELAY)
                self.logger.warning(
                    "[%s] Rate limited. Retrying in %.1fs (attempt %d/%d)...",
                    self.agent_name,
                    wait,
                    attempt + 1,
                    RATE_LIMIT_MAX_RETRIES,
                )
                await asyncio.sleep(wait)
                delay *= 2
            except ProviderError as e:
                if attempt >= RATE_LIMIT_MAX_RETRIES - 1:
                    raise
                self.logger.warning(
                    "[%s] Transient provider error: %s. Retrying...",
                    self.agent_name,
                    e,
                )
                await asyncio.sleep(2.0)
        # Should never reach here
        raise RuntimeError("Backoff loop exited without returning")

    def _get_schema_json(self, schema_cls: type[BaseModel]) -> str:
        """Return cached JSON schema string for a Pydantic model."""
        if schema_cls not in self.__class__._schema_cache:
            self.__class__._schema_cache[schema_cls] = json.dumps(
                schema_cls.model_json_schema(), indent=2
            )
        return self.__class__._schema_cache[schema_cls]

    def _extract_json(self, text: str) -> dict:
        """Extract the first valid JSON object from an LLM response.

        Tries three strategies in order:
          1. Direct parse (response is pure JSON)
          2. Extract from a ```json ... ``` fenced block
          3. Bracket scan from first { to last } (greedy, handles nesting)
        """
        text = text.strip()

        # 1. Direct parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. Fenced JSON block — use greedy match so nested {} are captured
        match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        # 3. Greedy bracket scan from first { to last }
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        raise json.JSONDecodeError("Could not extract JSON from LLM response", text, 0)

    def _extract_code_block(self, text: str) -> str:
        """Extract Python code from a fenced block, or return the raw text."""
        match = re.search(r"```(?:python)?\s*(.*?)```", text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return text.strip()
