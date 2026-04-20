import logging
import logging.config
import os

from dotenv import load_dotenv

load_dotenv()

# ── LLM Provider ─────────────────────────────────────────────────────────────
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "anthropic")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

# ── Default models per provider ───────────────────────────────────────────────
_PROVIDER_MODELS: dict[str, dict[str, str]] = {
    "anthropic": {
        "heavy": "claude-sonnet-4-6",
        "light": "claude-haiku-4-5-20251001",
    },
    "openai": {
        "heavy": "gpt-4o",
        "light": "gpt-4o-mini",
    },
    "groq": {
        "heavy": "llama-3.3-70b-versatile",
        "light": "llama-3.1-8b-instant",
    },
}

_models = _PROVIDER_MODELS.get(LLM_PROVIDER, _PROVIDER_MODELS["anthropic"])
HEAVY_MODEL = os.getenv("OPTIMATE_HEAVY_MODEL", _models["heavy"])
LIGHT_MODEL = os.getenv("OPTIMATE_LIGHT_MODEL", _models["light"])

# ── Pipeline limits ───────────────────────────────────────────────────────────
MAX_LLM_RETRIES = 3
MAX_EXECUTOR_RETRIES = 3
EXECUTOR_TIMEOUT_SECONDS = 60
LLM_MAX_TOKENS = 4096

# Exponential backoff for rate-limit errors (seconds)
RATE_LIMIT_BASE_DELAY = 5.0
RATE_LIMIT_MAX_DELAY = 60.0
RATE_LIMIT_MAX_RETRIES = 4

# ── Solver config ─────────────────────────────────────────────────────────────
SOLVER_PRIORITY: dict[str, list[str]] = {
    "assignment": ["pulp", "highs"],
    "inventory": ["pulp", "scipy"],
    "scheduling": ["ortools", "pulp"],
}

SCOUT_CONFIDENCE_THRESHOLD = 0.4

ARTIFACTS_BASE_DIR = os.getenv("OPTIMATE_BASE_DIR", "artifacts")

# Max columns to show in formulator prompt (guards against wide datasets)
MAX_FORMULATOR_COLUMNS = 40

# Max characters for variable summary in report prompt
MAX_VAR_SUMMARY_CHARS = 3000


def validate_config(provider: str | None = None) -> None:
    """Raise ConfigurationError if the required API key for the chosen provider is missing."""
    from optimatecore.exceptions import ConfigurationError

    p = provider or LLM_PROVIDER
    key_map = {
        "anthropic": ("ANTHROPIC_API_KEY", ANTHROPIC_API_KEY),
        "openai": ("OPENAI_API_KEY", OPENAI_API_KEY),
        "groq": ("GROQ_API_KEY", GROQ_API_KEY),
    }
    if p not in key_map:
        raise ConfigurationError(f"Unknown provider '{p}'. Choose from: {list(key_map)}")
    env_name, value = key_map[p]
    if not value:
        raise ConfigurationError(
            f"API key for provider '{p}' is not set. "
            f"Set the {env_name} environment variable (e.g. in .env)."
        )


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging for the application."""
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            },
        },
        "root": {
            "level": level,
            "handlers": ["console"],
        },
        # Suppress noisy third-party loggers
        "loggers": {
            "httpx": {"level": "WARNING"},
            "httpcore": {"level": "WARNING"},
            "anthropic": {"level": "WARNING"},
            "openai": {"level": "WARNING"},
        },
    })
