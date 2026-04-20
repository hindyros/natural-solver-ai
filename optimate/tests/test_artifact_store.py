"""Tests for ArtifactStore — read/write/atomic safety."""

import json
import pytest
from pydantic import BaseModel

from optimatecore.artifact_store import ArtifactStore
from optimatecore.exceptions import ArtifactNotFoundError


class _SampleModel(BaseModel):
    name: str
    value: int


@pytest.fixture
def store(tmp_path):
    return ArtifactStore(run_id="test_run", base_dir=str(tmp_path))


def test_write_and_read_dict(store):
    store.write("problem_brief", {"key": "value", "number": 42})
    result = store.read("problem_brief")
    assert result == {"key": "value", "number": 42}


def test_write_and_read_pydantic(store):
    model = _SampleModel(name="test", value=99)
    store.write("sample", model)
    result = store.read("sample")
    assert result["name"] == "test"
    assert result["value"] == 99


def test_write_creates_subdirectories(store):
    store.write("models/opp_1/spec", {"hello": "world"})
    assert store.exists("models/opp_1/spec")


def test_read_missing_raises(store):
    with pytest.raises(ArtifactNotFoundError):
        store.read("does_not_exist")


def test_write_text_and_read_text(store):
    code = "import pulp\nprint('hello')"
    store.write_text("models/opp_1/code", code, ext=".py")
    result = store.read_text("models/opp_1/code", ext=".py")
    assert result == code


def test_read_text_missing_raises(store):
    with pytest.raises(ArtifactNotFoundError):
        store.read_text("nonexistent", ext=".py")


def test_exists_false_for_missing(store):
    assert not store.exists("missing_key")


def test_exists_true_after_write(store):
    store.write("check_me", {"x": 1})
    assert store.exists("check_me")


def test_atomic_write_no_tmp_left_on_success(store):
    store.write("atomic_test", {"ok": True})
    # No .json.tmp file should remain
    tmp_files = list(store.run_dir_path().rglob("*.tmp"))
    assert tmp_files == [], f"Stale .tmp files found: {tmp_files}"


def test_overwrite_is_clean(store):
    store.write("overwrite_me", {"v": 1})
    store.write("overwrite_me", {"v": 2})
    assert store.read("overwrite_me")["v"] == 2


def test_run_dir_path_is_correct(store, tmp_path):
    expected = tmp_path / "test_run"
    assert store.run_dir_path() == expected
