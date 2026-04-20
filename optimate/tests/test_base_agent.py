"""Tests for BaseAgent utilities — JSON extraction and code block parsing."""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from optimatecore.artifact_store import ArtifactStore
from optimatecore.base_agent import BaseAgent
from optimatecore.llm_client import LLMClient


class _ConcreteAgent(BaseAgent):
    """Minimal concrete subclass for testing BaseAgent methods."""
    agent_name = "TestAgent"

    async def run(self):
        pass


@pytest.fixture
def agent(tmp_path):
    mock_client = MagicMock(spec=LLMClient)
    mock_client.usage = MagicMock()
    store = ArtifactStore(run_id="test", base_dir=str(tmp_path))
    return _ConcreteAgent(client=mock_client, store=store)


# ── _extract_json ─────────────────────────────────────────────────────────────

def test_extract_json_direct(agent):
    result = agent._extract_json('{"a": 1, "b": "hello"}')
    assert result == {"a": 1, "b": "hello"}


def test_extract_json_fenced_block(agent):
    text = '```json\n{"x": 42}\n```'
    assert agent._extract_json(text) == {"x": 42}


def test_extract_json_fenced_block_nested(agent):
    """Nested JSON objects must not be truncated by non-greedy regex."""
    text = '```json\n{"outer": {"inner": 1}}\n```'
    result = agent._extract_json(text)
    assert result == {"outer": {"inner": 1}}


def test_extract_json_bracket_scan(agent):
    text = "Here is the result: {\"key\": \"value\"} — end"
    assert agent._extract_json(text) == {"key": "value"}


def test_extract_json_with_preamble(agent):
    text = "Sure! Here is the JSON:\n\n{\"status\": \"ok\", \"count\": 3}"
    assert agent._extract_json(text) == {"status": "ok", "count": 3}


def test_extract_json_raises_on_garbage(agent):
    with pytest.raises(json.JSONDecodeError):
        agent._extract_json("this is not json at all")


def test_extract_json_empty_object(agent):
    assert agent._extract_json("{}") == {}


# ── _extract_code_block ────────────────────────────────────────────────────────

def test_extract_code_block_fenced(agent):
    text = "Here is the code:\n```python\nprint('hello')\n```"
    assert agent._extract_code_block(text) == "print('hello')"


def test_extract_code_block_unfenced(agent):
    code = "print('no fence')"
    assert agent._extract_code_block(code) == code


def test_extract_code_block_strips_whitespace(agent):
    text = "```python\n\n  x = 1\n\n```"
    assert agent._extract_code_block(text) == "x = 1"


# ── Schema cache ───────────────────────────────────────────────────────────────

def test_schema_cache_returns_same_object(agent):
    from pydantic import BaseModel as PM

    class _Schema(PM):
        x: int

    s1 = agent._get_schema_json(_Schema)
    s2 = agent._get_schema_json(_Schema)
    assert s1 is s2  # same object (cached)


def test_schema_cache_is_valid_json(agent):
    from optimatecore.schemas import ProblemBrief
    s = agent._get_schema_json(ProblemBrief)
    parsed = json.loads(s)
    assert "properties" in parsed
