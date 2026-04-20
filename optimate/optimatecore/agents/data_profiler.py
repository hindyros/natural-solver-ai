import asyncio
import json
import logging
from pathlib import Path
from typing import Any

import pandas as pd

from optimatecore.artifact_store import ArtifactStore
from optimatecore.base_agent import BaseAgent
from optimatecore.exceptions import DataLoadError
from optimatecore.schemas import DataInventory, ProblemBrief

logger = logging.getLogger(__name__)


class DataProfiler(BaseAgent):
    agent_name = "DataProfiler"
    system_prompt = (
        "You are a data scientist specializing in operations research. "
        "You receive statistical profiles of datasets and interpret them in the context "
        "of a business optimization problem. "
        "Identify which columns are likely decision-relevant: costs, capacities, demands, "
        "entity IDs, time indices, constraints. "
        "Be honest about data quality issues. "
        "Respond with valid JSON matching the required schema."
    )

    async def run(self, file_paths: list[str], brief: ProblemBrief | None = None) -> DataInventory:
        # Run pandas profiling in a thread so it doesn't block the event loop
        raw_profiles, total_rows = await asyncio.to_thread(
            self._profile_files, file_paths
        )

        schema = self._get_schema_json(DataInventory)
        context = (
            f"Client domain: {brief.domain}. Goal: {brief.primary_goal}"
            if brief
            else ""
        )

        prompt = (
            f"Interpret these dataset profiles in an optimization context.\n\n"
            f"{context}\n\n"
            f"RAW PROFILES:\n{json.dumps(raw_profiles, indent=2, default=str)}\n\n"
            f"TOTAL ROWS ACROSS ALL FILES: {total_rows}\n\n"
            f"Respond with JSON matching this schema:\n{schema}\n\n"
            f"For each column's optimization_role_hint, suggest its likely role "
            f"(e.g., 'cost coefficient', 'demand value', 'entity ID', 'capacity constraint', "
            f"'time index', 'binary flag'). "
            f"Be specific about detected_entity_types (e.g., 'workers', 'products', 'machines')."
        )
        result = await self._call_llm(prompt, DataInventory)
        self.store.write("data_inventory", result)
        logger.info(
            "[DataProfiler] Profiled %d file(s), %d total rows, %d columns",
            len(file_paths),
            total_rows,
            result.total_columns,
        )
        return result

    def _profile_files(self, file_paths: list[str]) -> tuple[list[dict], int]:
        """Pure-pandas statistical profiling — runs in a thread pool."""
        profiles = []
        total_rows = 0

        for fp in file_paths:
            path = Path(fp)
            try:
                if path.suffix.lower() == ".csv":
                    df = pd.read_csv(fp)
                elif path.suffix.lower() == ".json":
                    df = pd.read_json(fp)
                else:
                    profiles.append({"file": fp, "error": f"Unsupported format: {path.suffix}"})
                    continue
            except Exception as e:
                raise DataLoadError(f"Failed to load {fp}: {e}") from e

            total_rows += len(df)
            col_profiles = []

            for col in df.columns:
                series = df[col]
                null_pct = float(series.isna().mean())
                n_unique = int(series.nunique())
                # Use pd.notna() — handles both float NaN and pd.NA (nullable types)
                sample = [v for v in series.dropna().head(5).tolist() if pd.notna(v)]

                if pd.api.types.is_bool_dtype(series):
                    dtype = "boolean"
                    min_v = max_v = mean_v = None
                elif pd.api.types.is_numeric_dtype(series):
                    dtype = "numeric"
                    non_null = series.dropna()
                    min_v = float(non_null.min()) if len(non_null) else None
                    max_v = float(non_null.max()) if len(non_null) else None
                    mean_v = round(float(non_null.mean()), 4) if len(non_null) else None
                elif pd.api.types.is_datetime64_any_dtype(series):
                    dtype = "datetime"
                    min_v = max_v = mean_v = None
                else:
                    dtype = "categorical"
                    min_v = max_v = mean_v = None

                col_profiles.append({
                    "name": col,
                    "dtype": dtype,
                    "null_pct": round(null_pct, 4),
                    "n_unique": n_unique,
                    "sample_values": sample,
                    "min_val": min_v,
                    "max_val": max_v,
                    "mean_val": mean_v,
                })

            profiles.append({
                "file": str(path.name),
                "rows": len(df),
                "columns": col_profiles,
            })

        return profiles, total_rows
