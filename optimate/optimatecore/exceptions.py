class OptiMATEError(Exception):
    """Base exception for all OptiMATE errors."""


class AgentError(OptiMATEError):
    """LLM agent failed after all retries."""

    def __init__(self, agent_name: str, last_response: str, parse_error: str):
        self.agent_name = agent_name
        self.last_response = last_response
        self.parse_error = parse_error
        super().__init__(
            f"Agent '{agent_name}' failed after all retries. "
            f"Last parse error: {parse_error}"
        )


class RateLimitError(OptiMATEError):
    """LLM provider returned a rate-limit (429) response."""

    def __init__(self, provider: str, retry_after: float | None = None):
        self.provider = provider
        self.retry_after = retry_after
        msg = f"Rate limited by provider '{provider}'"
        if retry_after:
            msg += f" — retry after {retry_after:.1f}s"
        super().__init__(msg)


class ProviderError(OptiMATEError):
    """Transient provider error (5xx, connection reset, etc.)."""

    def __init__(self, provider: str, detail: str):
        self.provider = provider
        super().__init__(f"Provider '{provider}' error: {detail}")


class NoOpportunityFoundError(OptiMATEError):
    """All scouts returned low confidence — no viable opportunity found."""


class ExecutionError(OptiMATEError):
    """Executor exhausted all retry attempts without a successful solve."""

    def __init__(self, opportunity_id: str, attempts: int):
        self.opportunity_id = opportunity_id
        super().__init__(
            f"Execution failed for opportunity '{opportunity_id}' "
            f"after {attempts} attempt(s)."
        )


class DataLoadError(OptiMATEError):
    """Failed to load or parse an input data file."""


class ArtifactNotFoundError(OptiMATEError):
    """Requested artifact does not exist in the store."""


class ConfigurationError(OptiMATEError):
    """Invalid or missing configuration (e.g. API key not set)."""
