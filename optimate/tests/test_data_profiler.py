"""Tests for DataProfiler._profile_files — pure pandas, no LLM."""

import pytest
from pathlib import Path

from optimatecore.agents.data_profiler import DataProfiler
from optimatecore.artifact_store import ArtifactStore
from optimatecore.exceptions import DataLoadError
from unittest.mock import MagicMock

from optimatecore.llm_client import LLMClient


@pytest.fixture
def profiler(tmp_path):
    mock_client = MagicMock(spec=LLMClient)
    mock_client.usage = MagicMock()
    store = ArtifactStore(run_id="test", base_dir=str(tmp_path))
    return DataProfiler(client=mock_client, store=store)


@pytest.fixture
def simple_csv(tmp_path) -> str:
    p = tmp_path / "data.csv"
    p.write_text(
        "worker_id,cost,available\n"
        "W1,3.5,1\n"
        "W2,4.2,0\n"
        "W3,,1\n"  # missing cost
    )
    return str(p)


@pytest.fixture
def bool_csv(tmp_path) -> str:
    p = tmp_path / "bools.csv"
    p.write_text("flag\nTrue\nFalse\nTrue\n")
    return str(p)


def test_profile_basic_columns(profiler, simple_csv):
    profiles, total_rows = profiler._profile_files([simple_csv])
    assert total_rows == 3
    assert len(profiles) == 1
    cols = {c["name"]: c for c in profiles[0]["columns"]}
    assert cols["worker_id"]["dtype"] == "categorical"
    assert cols["cost"]["dtype"] == "numeric"
    assert cols["cost"]["null_pct"] == pytest.approx(1 / 3, rel=1e-3)
    assert cols["available"]["dtype"] == "numeric"


def test_profile_sample_values_no_nan(profiler, simple_csv):
    """sample_values must not contain NaN or pd.NA values."""
    import math
    profiles, _ = profiler._profile_files([simple_csv])
    cols = {c["name"]: c for c in profiles[0]["columns"]}
    for v in cols["cost"]["sample_values"]:
        assert not (isinstance(v, float) and math.isnan(v))


def test_profile_numeric_stats(profiler, simple_csv):
    profiles, _ = profiler._profile_files([simple_csv])
    cols = {c["name"]: c for c in profiles[0]["columns"]}
    cost = cols["cost"]
    assert cost["min_val"] == pytest.approx(3.5)
    assert cost["max_val"] == pytest.approx(4.2)
    assert cost["mean_val"] == pytest.approx(3.85, rel=1e-3)


def test_profile_unsupported_extension(profiler, tmp_path):
    bad = tmp_path / "data.xlsx"
    bad.write_bytes(b"fake")
    profiles, total_rows = profiler._profile_files([str(bad)])
    assert total_rows == 0
    assert "error" in profiles[0]


def test_profile_missing_file_raises(profiler):
    with pytest.raises(DataLoadError):
        profiler._profile_files(["/nonexistent/path/data.csv"])


def test_profile_multiple_files(profiler, simple_csv, tmp_path):
    csv2 = tmp_path / "data2.csv"
    csv2.write_text("x\n1\n2\n3\n4\n5\n")
    profiles, total_rows = profiler._profile_files([simple_csv, str(csv2)])
    assert total_rows == 8  # 3 + 5
    assert len(profiles) == 2


def test_profile_n_unique(profiler, simple_csv):
    profiles, _ = profiler._profile_files([simple_csv])
    cols = {c["name"]: c for c in profiles[0]["columns"]}
    assert cols["worker_id"]["n_unique"] == 3
    assert cols["available"]["n_unique"] == 2
