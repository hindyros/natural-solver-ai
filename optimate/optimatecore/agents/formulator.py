import logging

from optimatecore.artifact_store import ArtifactStore
from optimatecore.base_agent import BaseAgent
from optimatecore.config import HEAVY_MODEL, MAX_FORMULATOR_COLUMNS
from optimatecore.schemas import DataInventory, MathFormulation, OpportunityProposal, ProblemBrief

logger = logging.getLogger(__name__)


class Formulator(BaseAgent):
    agent_name = "Formulator"
    model = HEAVY_MODEL
    system_prompt = (
        "You are a senior Operations Research scientist. "
        "Your role is to produce a precise, complete mathematical formulation of an optimization problem. "
        "Your formulation must be:\n"
        "- Complete: every symbol defined, every constraint stated\n"
        "- Correct: types match (binary for yes/no decisions, continuous for quantities)\n"
        "- Implementable: a developer can directly write solver code from your formulation\n"
        "- Honest: state assumptions explicitly\n\n"
        "Use standard OR notation. Always respond with valid JSON."
    )

    async def run(
        self,
        opportunity: OpportunityProposal,
        brief: ProblemBrief,
        inventory: DataInventory,
    ) -> MathFormulation:
        schema = self._get_schema_json(MathFormulation)

        # Filter columns to only those needed, or cap at MAX_FORMULATOR_COLUMNS
        # to prevent prompt bloat on wide datasets.
        needed = set(opportunity.input_columns_needed)
        if needed:
            relevant_cols = [c for c in inventory.columns if c.name in needed]
        else:
            relevant_cols = inventory.columns[:MAX_FORMULATOR_COLUMNS]

        if len(relevant_cols) < len(inventory.columns):
            logger.debug(
                "[Formulator] Showing %d/%d columns in prompt",
                len(relevant_cols),
                len(inventory.columns),
            )

        columns_summary = "\n".join(
            f"  - {c.name} ({c.dtype}, {c.n_unique} unique values): {c.optimization_role_hint}"
            for c in relevant_cols
        )

        prompt = (
            f"Create a complete mathematical formulation for this optimization opportunity.\n\n"
            f"OPPORTUNITY:\n{opportunity.model_dump_json(indent=2)}\n\n"
            f"CLIENT CONTEXT:\n"
            f"  Primary goal: {brief.primary_goal}\n"
            f"  Domain: {brief.domain}\n"
            f"  Hard constraints mentioned: {brief.constraints_mentioned}\n\n"
            f"AVAILABLE DATA COLUMNS:\n{columns_summary}\n\n"
            f"FORMULATION REQUIREMENTS:\n"
            f"1. Define ALL decision variables with exact types (binary/integer/continuous)\n"
            f"2. State the objective function with mathematical expression\n"
            f"3. List ALL constraints — use the opportunity's constraints_sketch as a starting point\n"
            f"4. Map formulation parameters to actual data column names in data_mappings\n"
            f"5. State all assumptions explicitly\n"
            f"6. Recommend the specific solver (pulp, ortools, or scipy)\n\n"
            f"Respond with JSON matching this schema:\n{schema}\n\n"
            f"The opportunity_id must be '{opportunity.opportunity_id}'."
        )

        result = await self._call_llm(prompt, MathFormulation)
        self.store.write(f"models/{opportunity.opportunity_id}/spec", result)
        logger.info(
            "[Formulator] %d variables, %d constraints | solver: %s",
            len(result.decision_variables),
            len(result.constraints),
            result.solver_recommendation,
        )
        return result
