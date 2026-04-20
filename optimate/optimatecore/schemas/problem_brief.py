from typing import Literal
from pydantic import BaseModel, Field


class ProblemBrief(BaseModel):
    company_context: str = Field(description="Who the client is and what they do")
    primary_goal: str = Field(description="The main business objective to optimize")
    constraints_mentioned: list[str] = Field(
        description="Hard constraints named in the problem description"
    )
    data_sources_mentioned: list[str] = Field(
        description="Files, tables, or systems referenced as data sources"
    )
    business_kpis: list[str] = Field(
        description="Key performance indicators relevant to the problem"
    )
    domain: str = Field(
        description="Business domain, e.g. logistics, retail, manufacturing, healthcare"
    )
    problem_complexity: Literal["simple", "moderate", "complex"] = Field(
        description="Estimated complexity based on number of constraints and variables"
    )
    assumptions_logged: list[str] = Field(
        default_factory=list,
        description="Inferences made that were not explicitly stated in the description",
    )
    raw_description: str = Field(description="Original problem text, preserved verbatim")
