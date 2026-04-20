from typing import Any, Literal
from pydantic import BaseModel, Field


class ExecutionResult(BaseModel):
    attempt_number: int
    status: Literal["success", "error", "timeout"]
    stdout: str = ""
    stderr: str = ""
    runtime_seconds: float = 0.0


class SolutionResult(BaseModel):
    opportunity_id: str
    solver_used: str
    solve_status: Literal["optimal", "feasible", "infeasible", "unbounded", "timeout", "error"]
    objective_value: float | None = None
    solve_time_seconds: float = 0.0
    variable_summary: dict[str, Any] = Field(
        default_factory=dict,
        description="Key decision variable values in a human-readable form",
    )
    execution_attempts: list[ExecutionResult] = Field(default_factory=list)
    final_code: str = Field(description="The code that succeeded, or the last attempt")
    validation_passed: bool = False
    validation_notes: str = ""
