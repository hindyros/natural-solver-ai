import json
import logging

from optimatecore.artifact_store import ArtifactStore
from optimatecore.base_agent import BaseAgent
from optimatecore.exceptions import NoOpportunityFoundError
from optimatecore.schemas import OpportunityProposal, RankedOpportunities

logger = logging.getLogger(__name__)


class OpportunityRanker(BaseAgent):
    agent_name = "OpportunityRanker"
    system_prompt = (
        "You are a senior OR consultant responsible for prioritizing optimization opportunities. "
        "You receive proposals from specialist scouts and must select the single best opportunity "
        "to pursue based on: business impact, data readiness, and implementation feasibility. "
        "Be decisive and justify your choice concisely. "
        "Always respond with valid JSON."
    )

    async def run(self, proposals: list[OpportunityProposal]) -> RankedOpportunities:
        if not proposals:
            raise NoOpportunityFoundError("No valid proposals to rank.")

        if len(proposals) == 1:
            result = RankedOpportunities(
                opportunities=proposals,
                selected_opportunity_id=proposals[0].opportunity_id,
                ranking_rationale=(
                    f"Only one viable opportunity was detected: '{proposals[0].title}'. "
                    f"Proceeding with confidence score {proposals[0].confidence_score:.2f}."
                ),
            )
            self.store.write("ranked_opportunities", result)
            return result

        schema = self._get_schema_json(RankedOpportunities)
        proposals_json = json.dumps(
            [p.model_dump(mode="json") for p in proposals], indent=2
        )

        prompt = (
            f"Rank and select the best optimization opportunity from these proposals.\n\n"
            f"PROPOSALS:\n{proposals_json}\n\n"
            f"RANKING CRITERIA (in order of importance):\n"
            f"1. Data readiness — are the required columns actually available?\n"
            f"2. Business impact — how clearly does the opportunity address the client's primary goal?\n"
            f"3. Confidence score — how certain is the scout?\n"
            f"4. Implementation complexity — prefer lower complexity for similar impact\n\n"
            f"Select exactly ONE opportunity as 'selected_opportunity_id'. "
            f"Order 'opportunities' from best to worst. "
            f"Respond with JSON matching this schema:\n{schema}"
        )

        result = await self._call_llm(prompt, RankedOpportunities)
        self.store.write("ranked_opportunities", result)
        logger.info("[OpportunityRanker] Selected: '%s'", result.selected_opportunity_id)
        return result
