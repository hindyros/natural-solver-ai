"""Shared fixtures for OptiMATE tests."""

import pytest
import tempfile
from pathlib import Path


@pytest.fixture
def tmp_run_dir(tmp_path):
    """A temporary directory acting as an artifact store run directory."""
    return tmp_path


@pytest.fixture
def sample_csv(tmp_path) -> Path:
    """A minimal CSV for data profiler tests."""
    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "worker_id,shift_id,cost\n"
        "W1,S1,3.5\n"
        "W1,S2,4.2\n"
        "W2,S1,2.8\n"
        "W2,S2,5.1\n"
    )
    return csv_path


@pytest.fixture
def sample_problem_text() -> str:
    return (
        "We have 4 workers and 4 shifts. "
        "We want to assign each worker to exactly one shift to minimize total cost. "
        "Each shift must be covered by exactly one worker."
    )
