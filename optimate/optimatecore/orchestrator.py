import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from optimatecore.agents.business_analyst import BusinessAnalyst
from optimatecore.agents.data_profiler import DataProfiler
from optimatecore.agents.executor import Executor
from optimatecore.agents.formulator import Formulator
from optimatecore.agents.modeler import Modeler
from optimatecore.agents.opportunity_ranker import OpportunityRanker
from optimatecore.agents.report_writer import ReportWriter
from optimatecore.agents.scouts.assignment_scout import AssignmentScout
from optimatecore.agents.scouts.inventory_scout import InventoryScout
from optimatecore.agents.scouts.scheduling_scout import SchedulingScout
from optimatecore.artifact_store import ArtifactStore
from optimatecore.config import (
    ANTHROPIC_API_KEY,
    ARTIFACTS_BASE_DIR,
    GROQ_API_KEY,
    LLM_PROVIDER,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
)
from optimatecore.exceptions import NoOpportunityFoundError
from optimatecore.llm_client import LLMClient, build_client
from optimatecore.schemas import OpportunityProposal

logger = logging.getLogger(__name__)


class Orchestrator:
    """Top-level async pipeline coordinator."""

    def __init__(self, base_dir: str = ARTIFACTS_BASE_DIR, client: LLMClient | None = None):
        self.base_dir = base_dir
        self.client = client if client is not None else self._build_default_client()

    @staticmethod
    def _build_default_client() -> LLMClient:
        provider = LLM_PROVIDER
        if provider == "anthropic":
            return build_client("anthropic", api_key=ANTHROPIC_API_KEY)
        if provider == "openai":
            return build_client("openai", api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        if provider == "groq":
            return build_client("groq", api_key=GROQ_API_KEY)
        raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")

    async def run(
        self,
        problem_description: str,
        data_file_paths: list[str],
        run_id: str | None = None,
    ) -> str:
        run_id = run_id or self._make_run_id()
        store = ArtifactStore(run_id, self.base_dir)
        pipeline_start = time.monotonic()

        logger.info("Starting run: %s", run_id)
        logger.info("Provider: %s | Data files: %s", LLM_PROVIDER, data_file_paths)

        # ── LAYER 1: Business Analysis, then Data Profiling with brief ────────
        # BA runs first (fast) so the DataProfiler can use the problem brief
        # to contextualize its column interpretation.
        t0 = time.monotonic()
        logger.info("Layer 1: Business Analysis...")
        ba = BusinessAnalyst(self.client, store)
        brief = await ba.run(raw_description=problem_description)

        logger.info("Layer 1: Data Profiling...")
        dp = DataProfiler(self.client, store)
        inventory = await dp.run(file_paths=data_file_paths, brief=brief)
        logger.info("Layer 1 complete in %.1fs", time.monotonic() - t0)

        # ── LAYER 2: Parallel opportunity scouting ────────────────────────────
        t0 = time.monotonic()
        logger.info("Layer 2: Opportunity Scouting (parallel)...")
        scouts = [
            AssignmentScout(self.client, store),
            InventoryScout(self.client, store),
            SchedulingScout(self.client, store),
        ]

        raw_proposals = await asyncio.gather(
            *[scout.run(brief=brief, inventory=inventory) for scout in scouts],
            return_exceptions=True,
        )

        valid_proposals: list[OpportunityProposal] = []
        for i, result in enumerate(raw_proposals):
            if isinstance(result, Exception):
                logger.warning(
                    "Scout %s raised an exception: %s",
                    scouts[i].agent_name,
                    result,
                )
            elif result is not None:
                valid_proposals.append(result)

        if not valid_proposals:
            raise NoOpportunityFoundError(
                "No scouts detected a viable optimization opportunity. "
                "Please provide more specific problem data."
            )

        logger.info(
            "Layer 2 complete in %.1fs — %d viable proposal(s)",
            time.monotonic() - t0,
            len(valid_proposals),
        )

        # ── LAYER 3: Rank and select ──────────────────────────────────────────
        t0 = time.monotonic()
        logger.info("Layer 3: Ranking opportunities...")
        ranker = OpportunityRanker(self.client, store)
        ranked = await ranker.run(proposals=valid_proposals)

        selected = next(
            (p for p in valid_proposals if p.opportunity_id == ranked.selected_opportunity_id),
            valid_proposals[0],
        )
        logger.info(
            "Layer 3 complete in %.1fs — selected: '%s'",
            time.monotonic() - t0,
            selected.title,
        )

        # ── LAYER 4: Formulate → Model → Execute ─────────────────────────────
        t0 = time.monotonic()
        logger.info("Layer 4: Formulation, Modeling, Execution...")

        formulator = Formulator(self.client, store)
        formulation = await formulator.run(
            opportunity=selected, brief=brief, inventory=inventory
        )

        modeler = Modeler(self.client, store)
        await modeler.run(
            formulation=formulation,
            inventory=inventory,
            opportunity_id=selected.opportunity_id,
        )

        executor = Executor(self.client, store)
        solution = await executor.run(
            opportunity_id=selected.opportunity_id,
            formulation=formulation,
            data_files=self._load_data_for_executor(data_file_paths),
        )
        logger.info(
            "Layer 4 complete in %.1fs — solve status: %s",
            time.monotonic() - t0,
            solution.solve_status,
        )

        # ── LAYER 5: Report ───────────────────────────────────────────────────
        t0 = time.monotonic()
        logger.info("Layer 5: Writing report...")
        writer = ReportWriter(self.client, store)
        report_path = await writer.run(
            run_id=run_id,
            brief=brief,
            inventory=inventory,
            ranked=ranked,
            formulation=formulation,
            solution=solution,
        )
        logger.info("Layer 5 complete in %.1fs", time.monotonic() - t0)

        total_time = time.monotonic() - pipeline_start
        logger.info(
            "Run complete: %s | Total time: %.1fs | %s",
            run_id,
            total_time,
            self.client.usage,
        )
        return report_path

    def _make_run_id(self) -> str:
        return f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _load_data_for_executor(self, file_paths: list[str]) -> dict[str, Any]:
        """Load data files into column-oriented arrays for solver code.

        Each CSV column becomes a list keyed by column name.
        JSON files are merged directly into the dict.
        No row-dict duplication — avoids 2x data bloat.
        """
        combined: dict[str, Any] = {}
        for fp in file_paths:
            path = Path(fp)
            try:
                if path.suffix.lower() == ".csv":
                    df = pd.read_csv(fp)
                    for col in df.columns:
                        combined[col] = df[col].tolist()
                    # Also expose unique values of likely ID columns
                    for col in df.columns:
                        if df[col].dtype == object or df[col].nunique() < len(df) * 0.5:
                            unique_key = f"{col}_unique"
                            if unique_key not in combined:
                                combined[unique_key] = df[col].unique().tolist()
                elif path.suffix.lower() == ".json":
                    data = json.loads(path.read_text())
                    if isinstance(data, dict):
                        combined.update(data)
                    else:
                        combined[path.stem] = data
            except Exception as e:
                logger.warning("Could not load %s: %s", fp, e)
        return combined
