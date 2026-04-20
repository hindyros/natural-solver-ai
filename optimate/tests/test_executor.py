"""Tests for Executor — status mapping and subprocess result handling."""

import pytest

from optimatecore.agents.executor import Executor


class TestMapStatus:
    """_map_status must correctly handle all solver status strings."""

    def _ms(self, s: str) -> str:
        return Executor._map_status(s)

    def test_optimal(self):
        assert self._ms("Optimal") == "optimal"
        assert self._ms("OPTIMAL") == "optimal"

    def test_infeasible_not_confused_with_feasible(self):
        """Key regression: 'infeasible' contains 'feasible' as substring."""
        assert self._ms("Infeasible") == "infeasible"
        assert self._ms("INFEASIBLE") == "infeasible"
        assert self._ms("infeasible") == "infeasible"

    def test_feasible(self):
        assert self._ms("Feasible") == "feasible"
        assert self._ms("feasible") == "feasible"

    def test_unbounded(self):
        assert self._ms("Unbounded") == "unbounded"

    def test_timeout_variants(self):
        assert self._ms("Time Limit") == "timeout"
        assert self._ms("time_limit") == "timeout"
        assert self._ms("timeout") == "timeout"

    def test_unknown_falls_back_to_error(self):
        assert self._ms("Not Solved") == "error"
        assert self._ms("") == "error"
        assert self._ms("unknown_status_xyz") == "error"

    def test_ortools_optimal(self):
        assert self._ms("OPTIMAL") == "optimal"

    def test_ortools_feasible(self):
        assert self._ms("FEASIBLE") == "feasible"

    def test_pulp_infeasible(self):
        # PuLP returns "Infeasible"
        assert self._ms("Infeasible") == "infeasible"
