"""Tests for LLMClient — UsageStats accumulation and error mapping."""

import pytest
from optimatecore.llm_client import UsageStats


class TestUsageStats:
    def test_initial_state(self):
        u = UsageStats()
        assert u.total_calls == 0
        assert u.total_input_tokens == 0
        assert u.total_output_tokens == 0
        assert u.total_tokens == 0

    def test_update_accumulates(self):
        u = UsageStats()
        u.update(100, 50)
        u.update(200, 80)
        assert u.total_calls == 2
        assert u.total_input_tokens == 300
        assert u.total_output_tokens == 130
        assert u.total_tokens == 430

    def test_str_representation(self):
        u = UsageStats()
        u.update(1000, 500)
        s = str(u)
        assert "1 calls" in s
        assert "1,000" in s
        assert "500" in s
