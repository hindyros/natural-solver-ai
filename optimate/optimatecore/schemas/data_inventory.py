from typing import Any
from pydantic import BaseModel, Field


class ColumnProfile(BaseModel):
    name: str
    dtype: str = Field(description="numeric, categorical, datetime, or boolean")
    null_pct: float = Field(ge=0.0, le=1.0)
    n_unique: int
    sample_values: list[Any] = Field(description="Up to 5 representative values")
    min_val: float | None = None
    max_val: float | None = None
    mean_val: float | None = None
    optimization_role_hint: str = Field(
        description="LLM interpretation, e.g. 'likely a cost column'"
    )


class DataInventory(BaseModel):
    files_profiled: list[str]
    total_rows: int
    total_columns: int
    columns: list[ColumnProfile]
    detected_entity_types: list[str] = Field(
        description="e.g. ['workers', 'shifts', 'locations']"
    )
    data_quality_issues: list[str] = Field(
        description="Missing data warnings, type mismatches, outliers"
    )
    profiler_notes: str = Field(
        description="Free-form observations about the dataset in optimization context"
    )
