import json
import logging
from abc import abstractmethod

from optimatecore.artifact_store import ArtifactStore
from optimatecore.base_agent import BaseAgent
from optimatecore.config import SCOUT_CONFIDENCE_THRESHOLD
from optimatecore.schemas import DataInventory, OpportunityProposal, ProblemBrief

logger = logging.getLogger(__name__)


class BaseScout(BaseAgent):
    scout_type: str = ""
    domain_keywords: list[str] = []

    async def run(
        self,
        brief: ProblemBrief,
        inventory: DataInventory,
    ) -> OpportunityProposal | None:
        schema = self._get_schema_json(OpportunityProposal)
        columns_summary = "\n".join(
            f"  - {c.name} ({c.dtype}): {c.optimization_role_hint}"
            for c in inventory.columns
        )
        entities = (
            ", ".join(inventory.detected_entity_types)
            if inventory.detected_entity_types
            else "unknown"
        )

        prompt = (
            f"{self._scout_context()}\n\n"
            f"CLIENT PROBLEM:\n"
            f"  Goal: {brief.primary_goal}\n"
            f"  Domain: {brief.domain}\n"
            f"  Constraints mentioned: {brief.constraints_mentioned}\n\n"
            f"DATA AVAILABLE:\n"
            f"  Files: {inventory.files_profiled}\n"
            f"  Entity types detected: {entities}\n"
            f"  Columns:\n{columns_summary}\n\n"
            f"TASK: Determine whether a {self.scout_type} optimization opportunity exists.\n"
            f"If you find NO clear opportunity, set confidence_score below {SCOUT_CONFIDENCE_THRESHOLD} "
            f"and explain why in business_value.\n\n"
            f"Respond with JSON matching this schema:\n{schema}\n\n"
            f"The opportunity_id must be '{self.scout_type}_1'.\n"
            f"The scout_type must be '{self.scout_type}'.\n"
        )

        proposal = await self._call_llm(prompt, OpportunityProposal)

        if proposal.confidence_score >= SCOUT_CONFIDENCE_THRESHOLD:
            self.store.write(f"opportunities/{self.scout_type}", proposal)
            logger.info(
                "[%s] Opportunity found: '%s' (confidence=%.2f)",
                self.__class__.__name__,
                proposal.title,
                proposal.confidence_score,
            )
            return proposal
        else:
            logger.info(
                "[%s] No strong opportunity (confidence=%.2f)",
                self.__class__.__name__,
                proposal.confidence_score,
            )
            return None

    @abstractmethod
    def _scout_context(self) -> str:
        """Return the scout-specific context describing what it looks for."""
