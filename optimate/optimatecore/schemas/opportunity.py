from typing import Literal
from pydantic import BaseModel, Field


class OpportunityProposal(BaseModel):
    opportunity_id: str = Field(description="Unique ID, e.g. 'assignment_1'")
    scout_type: Literal["assignment", "inventory", "scheduling"]
    title: str = Field(description="Short title, e.g. 'Shift-to-Worker Assignment Optimization'")
    business_value: str = Field(
        description="Plain English description of potential savings or gains"
    )
    problem_class: str = Field(description="OR problem class, e.g. 'Linear Assignment Problem'")
    solver_recommendation: str = Field(description="Recommended solver: pulp, ortools, scipy")
    input_columns_needed: list[str] = Field(
        description="Column names from the data inventory that this model needs"
    )
    decision_variables_sketch: list[str] = Field(
        description="Natural language sketch of decision variables"
    )
    objective_sketch: str = Field(description="Natural language objective statement")
    constraints_sketch: list[str] = Field(
        description="Natural language list of constraints"
    )
    estimated_complexity: Literal["low", "medium", "high"]
    confidence_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Scout's confidence that this opportunity applies (0–1)",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Assumptions made in proposing this opportunity",
    )


class RankedOpportunities(BaseModel):
    opportunities: list[OpportunityProposal] = Field(
        description="All valid proposals, ordered best first"
    )
    selected_opportunity_id: str = Field(
        description="The opportunity ID chosen for formulation and solving"
    )
    ranking_rationale: str = Field(
        description="Why the selected opportunity was chosen over others"
    )
