import json
import logging
from datetime import date

from optimatecore.artifact_store import ArtifactStore
from optimatecore.base_agent import BaseAgent
from optimatecore.config import HEAVY_MODEL, MAX_VAR_SUMMARY_CHARS
from optimatecore.schemas import (
    DataInventory,
    MathFormulation,
    ProblemBrief,
    RankedOpportunities,
    SolutionResult,
)

logger = logging.getLogger(__name__)

# Hard cap on total prompt characters to stay well within context limits.
# Structured data sections are trimmed before the prompt is assembled.
_MAX_PROMPT_CHARS = 12_000


class ReportWriter(BaseAgent):
    agent_name = "ReportWriter"
    model = HEAVY_MODEL
    system_prompt = (
        "You are a senior management consultant writing an optimization analysis report. "
        "Your writing must be:\n"
        "- Executive-friendly in the summary: plain language, business impact first\n"
        "- Technically precise in the methodology section\n"
        "- Actionable in recommendations: specific, numbered actions\n"
        "- Honest about limitations and assumptions\n\n"
        "Never use jargon without explanation. "
        "Always lead with business value. "
        "Quantify impact wherever the data supports it. "
        "Use consulting conventions: action-oriented language, visual-first tables.\n\n"
        "Math formatting rules (strictly required):\n"
        "- Wrap ALL mathematical expressions in LaTeX delimiters.\n"
        "- Inline math: $x_i$, $\\sum_i$, $\\leq$, etc.\n"
        "- Block math (own line, centered): $$\\text{Maximize} \\sum_{i=1}^{n} p_i x_i$$\n"
        "- Never write raw math without delimiters (e.g. never write 'sum_i p_i x_i', always '$$\\sum_i p_i x_i$$').\n"
        "- Use standard LaTeX notation: \\sum, \\leq, \\geq, \\cdot, \\in, \\forall, \\text{}, etc."
    )

    async def run(
        self,
        run_id: str,
        brief: ProblemBrief,
        inventory: DataInventory,
        ranked: RankedOpportunities,
        formulation: MathFormulation,
        solution: SolutionResult,
    ) -> str:
        today = date.today().isoformat()

        opp_landscape_rows = "\n".join(
            f"| {o.scout_type.title()} | {o.title} | {o.confidence_score:.0%} | {o.estimated_complexity} |"
            for o in ranked.opportunities
        )

        # Guard variable summary size
        var_summary_raw = json.dumps(solution.variable_summary, indent=2, default=str)
        var_summary_text = var_summary_raw[:MAX_VAR_SUMMARY_CHARS]
        if len(var_summary_raw) > MAX_VAR_SUMMARY_CHARS:
            var_summary_text += "\n... (truncated)"

        assumptions_all = list(brief.assumptions_logged) + list(formulation.assumptions)
        assumptions_text = (
            "\n".join(f"- {a}" for a in assumptions_all) if assumptions_all else "- None stated."
        )

        # Cap constraints and variables tables to avoid runaway prompts
        constraints_text = "\n".join(
            f"- **{c.label}**: {c.description} `{c.expression}`"
            for c in formulation.constraints[:20]
        )
        variables_text = "\n".join(
            f"| `{v.symbol}` | {v.shape} | {v.var_type} | {v.definition} |"
            for v in formulation.decision_variables[:20]
        )

        solve_summary = (
            f"**Status:** {solution.solve_status.upper()}  \n"
            f"**Objective Value:** {solution.objective_value}  \n"
            f"**Solver:** {solution.solver_used}  \n"
            f"**Execution Attempts:** {len(solution.execution_attempts)}"
        )

        prompt = (
            f"Write a complete consulting-grade optimization report in Markdown.\n\n"
            f"Use this exact structure and fill in each section with analysis:\n\n"
            f"# Optimization Analysis Report\n"
            f"**Client:** {brief.company_context}  \n"
            f"**Date:** {today}  \n"
            f"**Run ID:** {run_id}\n\n"
            f"---\n\n"
            f"## Executive Summary\n"
            f"[Write 2-3 paragraphs: what optimization was identified, what was done, "
            f"and what the result means in business terms. Lead with impact. "
            f"Objective value was: {solution.objective_value}, status: {solution.solve_status}]\n\n"
            f"## Problem Understanding\n"
            f"**Primary Goal:** {brief.primary_goal}  \n"
            f"**Domain:** {brief.domain}  \n"
            f"**Complexity:** {brief.problem_complexity}  \n"
            f"**Constraints Mentioned:** {', '.join(brief.constraints_mentioned) or 'None explicitly stated'}\n\n"
            f"[Add 1-2 paragraphs contextualizing the problem.]\n\n"
            f"## Data Profiled\n"
            f"**Files Analyzed:** {', '.join(inventory.files_profiled)}  \n"
            f"**Total Records:** {inventory.total_rows}  \n"
            f"**Entities Identified:** {', '.join(inventory.detected_entity_types)}\n\n"
            f"[Describe key data characteristics and any quality issues: {inventory.data_quality_issues}]\n\n"
            f"## Opportunity Landscape\n"
            f"| Scout | Opportunity | Confidence | Complexity |\n"
            f"|-------|-------------|------------|------------|\n"
            f"{opp_landscape_rows}\n\n"
            f"**Selected:** {ranked.selected_opportunity_id}  \n"
            f"**Rationale:** {ranked.ranking_rationale}\n\n"
            f"## Mathematical Formulation\n"
            f"**Problem Type:** {formulation.problem_type}  \n"
            f"**Objective:** {formulation.objective_sense.upper()} `{formulation.objective_expression}`\n\n"
            f"### Decision Variables\n"
            f"| Symbol | Shape | Type | Definition |\n"
            f"|--------|-------|------|------------|\n"
            f"{variables_text}\n\n"
            f"### Constraints\n"
            f"{constraints_text}\n\n"
            f"## Solution Results\n"
            f"{solve_summary}\n\n"
            f"### Key Decisions\n"
            f"[Translate the variable_summary below into plain business language — "
            f"which entities were assigned where, what quantities were ordered, etc.]\n\n"
            f"```json\n{var_summary_text}\n```\n\n"
            f"## Recommendations\n"
            f"[Write 3-5 specific, numbered action items the client should take based on these results. "
            f"Be concrete and business-oriented.]\n\n"
            f"## Assumptions & Limitations\n"
            f"{assumptions_text}\n\n"
            f"[Add any additional caveats about the model or data.]\n\n"
            f"## Technical Appendix\n"
            f"**Solver Used:** {solution.solver_used}  \n"
            f"**Execution Attempts:** {len(solution.execution_attempts)}  \n"
            f"**Validation Passed:** {solution.validation_passed}  \n"
            f"**Validation Notes:** {solution.validation_notes}\n"
        )

        if len(prompt) > _MAX_PROMPT_CHARS:
            logger.warning(
                "[ReportWriter] Prompt is %d chars (cap: %d) — some content was pre-trimmed.",
                len(prompt),
                _MAX_PROMPT_CHARS,
            )

        report_md = await self._call_llm_text(prompt)
        report_path = self.store.write_text("report", report_md, ext=".md")
        logger.info("[ReportWriter] Report written (%d lines)", len(report_md.splitlines()))
        return str(report_path)
