import json
import os
from pathlib import Path

from pydantic import BaseModel

from optimatecore.exceptions import ArtifactNotFoundError


class ArtifactStore:
    """Shared artifact store for a single pipeline run.

    All agents read from and write to this store using logical keys.
    All writes are atomic (write to .tmp then rename) so a crash mid-write
    never leaves a corrupted artifact file.

    Key examples:
      "problem_brief"              → artifacts/{run_id}/problem_brief.json
      "opportunities/assignment"   → artifacts/{run_id}/opportunities/assignment.json
      "models/assignment_1/spec"   → artifacts/{run_id}/models/assignment_1/spec.json
      "models/assignment_1/code"   → artifacts/{run_id}/models/assignment_1/code.py
      "report"                     → artifacts/{run_id}/report.md
    """

    def __init__(self, run_id: str, base_dir: str = "artifacts"):
        self.run_id = run_id
        self.run_dir = Path(base_dir).resolve() / run_id
        self.run_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str, ext: str) -> Path:
        path = self.run_dir / key
        if not path.suffix:
            path = path.with_suffix(ext)
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def _atomic_write(self, path: Path, content: str) -> None:
        """Write content atomically: write to .tmp then rename."""
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_text(content, encoding="utf-8")
            # os.replace is atomic on POSIX and Windows (same filesystem)
            os.replace(tmp, path)
        except Exception:
            try:
                tmp.unlink(missing_ok=True)
            except OSError:
                pass
            raise

    def write(self, key: str, data: dict | BaseModel) -> Path:
        path = self._resolve(key, ".json")
        if isinstance(data, BaseModel):
            payload = data.model_dump(mode="json")
        else:
            payload = data
        self._atomic_write(path, json.dumps(payload, indent=2, default=str))
        return path

    def read(self, key: str) -> dict:
        path = self._resolve(key, ".json")
        if not path.exists():
            raise ArtifactNotFoundError(f"Artifact not found: {path}")
        return json.loads(path.read_text(encoding="utf-8"))

    def write_text(self, key: str, content: str, ext: str = ".py") -> Path:
        path = self._resolve(key, ext)
        self._atomic_write(path, content)
        return path

    def read_text(self, key: str, ext: str = ".py") -> str:
        path = self._resolve(key, ext)
        if not path.exists():
            raise ArtifactNotFoundError(f"Artifact not found: {path}")
        return path.read_text(encoding="utf-8")

    def exists(self, key: str, ext: str = ".json") -> bool:
        return self._resolve(key, ext).exists()

    def run_dir_path(self) -> Path:
        return self.run_dir
