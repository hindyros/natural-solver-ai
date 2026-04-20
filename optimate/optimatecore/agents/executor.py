import json
import logging
from pathlib import Path
from typing import Any

from optimatecore.artifact_store import ArtifactStore
from optimatecore.base_agent import BaseAgent
from optimatecore.config import MAX_EXECUTOR_RETRIES
from optimatecore.sandbox import run_sandboxed
from optimatecore.schemas import ExecutionResult, MathFormulation, SolutionResult

logger = logging.getLogger(__name__)


class Executor(BaseAgent):
    agent_name = "Executor"
    system_prompt = (
        "You are an expert Python debugger specializing in optimization code. "
        "You receive failing solver code with its error output and the original "
        "mathematical formulation as ground truth. "
        "Your job is to fix ONLY implementation bugs — never change the mathematical logic. "
        "Common issues to look for:\n"
        "- Wrong variable names or data keys\n"
        "- Incorrect solver API usage (method names, parameter types)\n"
        "- Shape/dimension mismatches in arrays\n"
        "- Missing imports\n"
        "- Data type errors (string vs int vs float)\n"
        "Return ONLY the corrected Python code, no explanation."
    )

    async def run(
        self,
        opportunity_id: str,
        formulation: MathFormulation,
        data_files: dict[str, Any],
    ) -> SolutionResult:
        exec_dir = self.store.run_dir_path() / "models" / opportunity_id
        exec_dir.mkdir(parents=True, exist_ok=True)

        # Write data.json for the subprocess
        (exec_dir / "data.json").write_text(
            json.dumps(data_files, indent=2, default=str)
        )

        code = self.store.read_text(f"models/{opportunity_id}/code", ext=".py")
        attempts: list[ExecutionResult] = []

        for attempt in range(MAX_EXECUTOR_RETRIES):
            code_file = exec_dir / f"code_attempt_{attempt}.py"
            code_file.write_text(code)

            logger.info(
                "[Executor] Attempt %d/%d for '%s'...",
                attempt + 1,
                MAX_EXECUTOR_RETRIES,
                opportunity_id,
            )
            exec_result = await run_sandboxed(code_file, exec_dir, attempt)
            attempts.append(exec_result)

            if exec_result.status == "success":
                solution_path = exec_dir / "solution_output.json"
                if solution_path.exists():
                    raw = json.loads(solution_path.read_text())
                else:
                    raw = {"status": "error", "objective": None, "variables": {}}

                solve_status = self._map_status(raw.get("status", "error"))
                solution = SolutionResult(
                    opportunity_id=opportunity_id,
                    solver_used=formulation.solver_recommendation,
                    solve_status=solve_status,
                    objective_value=raw.get("objective"),
                    solve_time_seconds=exec_result.runtime_seconds,
                    variable_summary=raw.get("variables", {}),
                    execution_attempts=attempts,
                    final_code=code,
                    validation_passed=solve_status in ("optimal", "feasible"),
                    validation_notes=f"Solved after {attempt + 1} attempt(s).",
                )
                self.store.write(f"models/{opportunity_id}/solution", solution)
                logger.info(
                    "[Executor] Success — status: %s, objective: %s",
                    solve_status,
                    raw.get("objective"),
                )
                return solution

            # Attempt failed — debug if retries remain
            if attempt < MAX_EXECUTOR_RETRIES - 1:
                logger.info(
                    "[Executor] Error on attempt %d, requesting debug fix...",
                    attempt + 1,
                )
                code = await self._debug_code(
                    code, exec_result.stderr, formulation, attempt, data_files
                )

        # All attempts exhausted
        solution = SolutionResult(
            opportunity_id=opportunity_id,
            solver_used=formulation.solver_recommendation,
            solve_status="error",
            execution_attempts=attempts,
            final_code=code,
            validation_passed=False,
            validation_notes=f"All {MAX_EXECUTOR_RETRIES} execution attempts failed.",
        )
        self.store.write(f"models/{opportunity_id}/solution", solution)
        logger.warning("[Executor] All attempts failed for '%s'.", opportunity_id)
        return solution

    async def _debug_code(
        self,
        code: str,
        error_output: str,
        formulation: MathFormulation,
        attempt_number: int,
        data_files: dict[str, Any] | None = None,
    ) -> str:
        if data_files is not None:
            preview_lines = []
            for k, v in data_files.items():
                if isinstance(v, list):
                    sample = v[:3]
                    preview_lines.append(f'  "{k}": {sample}  # list of {len(v)}, type={type(v[0]).__name__ if v else "unknown"}')
                elif isinstance(v, dict):
                    sample_keys = list(v.keys())[:3]
                    preview_lines.append(f'  "{k}": {{...}}  # dict with keys {sample_keys}')
                else:
                    preview_lines.append(f'  "{k}": {repr(v)}')
            keys_section = (
                "AVAILABLE DATA KEYS and sample values from data.json "
                "(use EXACTLY these key names — do NOT invent keys):\n"
                + "\n".join(preview_lines) + "\n\n"
            )
        else:
            keys_section = ""
        prompt = (
            f"Fix this failing optimization code. Attempt #{attempt_number + 1}.\n\n"
            f"MATHEMATICAL FORMULATION (ground truth — do not change the math):\n"
            f"{formulation.model_dump_json(indent=2)}\n\n"
            f"{keys_section}"
            f"FAILING CODE:\n```python\n{code}\n```\n\n"
            f"ERROR OUTPUT:\n```\n{error_output[:3000]}\n```\n\n"
            f"Return ONLY the corrected Python code."
        )
        fixed_text = await self._call_llm_text(prompt)
        return self._extract_code_block(fixed_text)

    @staticmethod
    def _map_status(raw_status: str) -> str:
        """Map solver status string to a canonical solve_status value.

        Checks more specific strings first to avoid substring collisions
        (e.g. "infeasible" contains "feasible").
        """
        s = raw_status.lower()
        if "infeasible" in s:
            return "infeasible"
        if "unbounded" in s:
            return "unbounded"
        if "optimal" in s:
            return "optimal"
        if "feasible" in s:
            return "feasible"
        if "timeout" in s or "time_limit" in s:
            return "timeout"
        return "error"
