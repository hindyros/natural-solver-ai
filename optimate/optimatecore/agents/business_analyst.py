import logging

from optimatecore.artifact_store import ArtifactStore
from optimatecore.base_agent import BaseAgent
from optimatecore.schemas import ProblemBrief

logger = logging.getLogger(__name__)


class BusinessAnalyst(BaseAgent):
    agent_name = "BusinessAnalyst"
    system_prompt = (
        "You are a senior business analyst at an operations research consulting firm. "
        "Your role is to read a client's problem description and extract structured information. "
        "Focus on: what the client does, what they want to optimize, what constraints they mentioned, "
        "what data they have, and what success looks like. "
        "Be precise — only extract information explicitly stated or strongly implied. "
        "When you make an inference not explicitly stated, record it in assumptions_logged. "
        "Always respond with valid JSON matching the required schema."
    )

    async def run(self, raw_description: str) -> ProblemBrief:
        schema = self._get_schema_json(ProblemBrief)
        prompt = (
            f"Analyze this client problem description and extract a structured Problem Brief.\n\n"
            f"PROBLEM DESCRIPTION:\n{raw_description}\n\n"
            f"Respond with JSON matching this exact schema:\n{schema}\n\n"
            f"Important:\n"
            f"- primary_goal must be a specific, measurable business objective (not just 'efficiency')\n"
            f"- constraints_mentioned should list only constraints explicitly named\n"
            f"- assumptions_logged should capture anything you inferred but wasn't stated\n"
            f"- raw_description must be the original text verbatim\n"
        )
        result = await self._call_llm(prompt, ProblemBrief)
        result = result.model_copy(update={"raw_description": raw_description})
        self.store.write("problem_brief", result)
        logger.info(
            "[BusinessAnalyst] Domain: %s | Complexity: %s",
            result.domain,
            result.problem_complexity,
        )
        return result
