from typing import Any, Literal
from pydantic import BaseModel, Field


class DecisionVariable(BaseModel):
    symbol: str = Field(description="Math symbol, e.g. 'x_ij'")
    shape: str = Field(description="Dimensions, e.g. '[n_workers x n_shifts]'")
    var_type: Literal["continuous", "integer", "binary"]
    definition: str = Field(description="Plain English definition")


class MathConstraint(BaseModel):
    label: str = Field(description="Short name, e.g. 'one_shift_per_worker'")
    expression: str = Field(description="Mathematical expression or plain math notation")
    description: str = Field(description="Plain English explanation")


class MathFormulation(BaseModel):
    opportunity_id: str
    problem_type: str = Field(description="e.g. 'Linear Assignment Problem'")
    objective_sense: Literal["minimize", "maximize"]
    objective_expression: str = Field(description="Mathematical objective expression")
    decision_variables: list[DecisionVariable]
    parameters: dict[str, str] = Field(
        description="symbol -> definition for all known data parameters"
    )
    constraints: list[MathConstraint]
    assumptions: list[str] = Field(
        description="Assumptions made in formulating the model"
    )
    solver_recommendation: str = Field(description="Solver to use: pulp, ortools, scipy")
    data_mappings: dict[str, str] = Field(
        default_factory=dict,
        description="Maps formulation parameters to dataset column names",
    )
