"""Subprocess execution with resource limits.

Provides a best-effort sandbox for running LLM-generated solver code.
On POSIX systems (Linux/macOS), resource limits are applied via
``resource.setrlimit`` in the child process before the target code runs.
On Windows, resource limits are not enforced (noted in the warning).

Limits applied (POSIX only):
    - CPU time: EXECUTOR_TIMEOUT_SECONDS + 5s hard cap
    - Virtual memory: 1 GB
    - Output file size: 50 MB
    - Open file descriptors: 64

Note: This is a process-level sandbox, not a container. The subprocess
still shares the host filesystem. For production deployments, wrap the
subprocess in a Docker container with ``--network none --read-only``.
"""

from __future__ import annotations

import asyncio
import logging
import platform
import sys
from pathlib import Path

from optimatecore.config import EXECUTOR_TIMEOUT_SECONDS
from optimatecore.schemas import ExecutionResult

logger = logging.getLogger(__name__)

_IS_POSIX = platform.system() in ("Linux", "Darwin")

# Resource limits (POSIX only)
_CPU_LIMIT_SECONDS = EXECUTOR_TIMEOUT_SECONDS + 5
_MEMORY_LIMIT_BYTES = 1 * 1024 ** 3       # 1 GB virtual memory
_FILE_SIZE_LIMIT_BYTES = 50 * 1024 ** 2   # 50 MB max output file
_MAX_OPEN_FILES = 64


def _apply_resource_limits() -> None:
    """Called as preexec_fn inside the child process (POSIX only)."""
    import resource

    try:
        # CPU time
        resource.setrlimit(resource.RLIMIT_CPU, (_CPU_LIMIT_SECONDS, _CPU_LIMIT_SECONDS))
    except (ValueError, resource.error):
        pass

    try:
        # Virtual memory (address space)
        resource.setrlimit(resource.RLIMIT_AS, (_MEMORY_LIMIT_BYTES, _MEMORY_LIMIT_BYTES))
    except (ValueError, resource.error):
        pass

    try:
        # Max file size the process can write
        resource.setrlimit(
            resource.RLIMIT_FSIZE,
            (_FILE_SIZE_LIMIT_BYTES, _FILE_SIZE_LIMIT_BYTES),
        )
    except (ValueError, resource.error):
        pass

    try:
        # Max open file descriptors
        resource.setrlimit(resource.RLIMIT_NOFILE, (_MAX_OPEN_FILES, _MAX_OPEN_FILES))
    except (ValueError, resource.error):
        pass


async def run_sandboxed(
    code_file: Path,
    exec_dir: Path,
    attempt_number: int,
) -> ExecutionResult:
    """Run ``code_file`` in a resource-limited subprocess.

    Always kills the child process on timeout — no orphaned subprocesses.
    """
    import time

    start = time.monotonic()
    preexec = _apply_resource_limits if _IS_POSIX else None

    if not _IS_POSIX:
        logger.warning(
            "Running on %s — resource limits are not enforced. "
            "Use Docker for production sandboxing.",
            platform.system(),
        )

    try:
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            str(code_file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(exec_dir),
            preexec_fn=preexec,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=float(EXECUTOR_TIMEOUT_SECONDS),
            )
        except asyncio.TimeoutError:
            # Kill the process — no orphans
            try:
                proc.kill()
                await proc.wait()
            except ProcessLookupError:
                pass  # already exited
            runtime = time.monotonic() - start
            logger.warning(
                "Attempt %d timed out after %.1fs", attempt_number + 1, runtime
            )
            return ExecutionResult(
                attempt_number=attempt_number,
                status="timeout",
                stderr=f"Execution timed out after {EXECUTOR_TIMEOUT_SECONDS}s.",
                runtime_seconds=round(runtime, 3),
            )

        runtime = time.monotonic() - start
        status = "success" if proc.returncode == 0 else "error"
        return ExecutionResult(
            attempt_number=attempt_number,
            status=status,
            stdout=stdout.decode(errors="replace"),
            stderr=stderr.decode(errors="replace"),
            runtime_seconds=round(runtime, 3),
        )

    except OSError as e:
        runtime = time.monotonic() - start
        return ExecutionResult(
            attempt_number=attempt_number,
            status="error",
            stderr=f"Failed to launch subprocess: {e}",
            runtime_seconds=round(runtime, 3),
        )
