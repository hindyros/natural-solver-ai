import logging

from optimatecore.artifact_store import ArtifactStore
from optimatecore.base_agent import BaseAgent
from optimatecore.schemas import DataInventory, MathFormulation
from optimatecore.solvers.solver_registry import SolverRegistry

logger = logging.getLogger(__name__)


class Modeler(BaseAgent):
    agent_name = "Modeler"
    system_prompt = (
        "You are a Python developer specializing in mathematical optimization. "
        "You generate complete, runnable Python solver code from a mathematical formulation. "
        "You fill in a given template with the specific details of the problem. "
        "Rules:\n"
        "- Only use the allowed solver library (pulp, ortools, or scipy)\n"
        "- Load all data from 'data.json' using: with open('data.json') as f: data = json.load(f)\n"
        "- At the end, print: OBJECTIVE_VALUE: {value}\n"
        "- Write results to 'solution_output.json' with keys: status, objective, variables\n"
        "- Handle infeasible/unbounded cases gracefully (print OBJECTIVE_VALUE: None)\n"
        "- Use meaningful variable names matching the formulation symbols\n"
        "Return ONLY the Python code, no explanation or markdown."
    )

    async def run(
        self,
        formulation: MathFormulation,
        inventory: DataInventory,
        opportunity_id: str,
    ) -> str:
        template = SolverRegistry.get_template(
            formulation.solver_recommendation,
            formulation.problem_type,
        )

        data_keys = list(set(
            list(formulation.data_mappings.values()) +
            [c.name for c in inventory.columns]
        ))

        prompt = (
            f"Generate complete Python solver code for this optimization problem.\n\n"
            f"MATHEMATICAL FORMULATION:\n{formulation.model_dump_json(indent=2)}\n\n"
            f"DATA AVAILABLE IN data.json:\n"
            f"The data.json file contains column arrays keyed by column name.\n"
            f"Available keys: {data_keys}\n"
            f"Data mappings (formulation param → data key): {formulation.data_mappings}\n\n"
            f"SOLVER TEMPLATE TO USE AS BASE:\n```python\n{template.skeleton()}\n```\n\n"
            f"INSTRUCTIONS:\n"
            f"1. Start from the template above\n"
            f"2. Replace all TODO comments with actual implementation\n"
            f"3. Use the exact column names from data_mappings to load data\n"
            f"4. Implement the objective and constraints exactly as formulated\n"
            f"5. The code must be complete and runnable with no placeholders\n\n"
            f"Return ONLY the Python code."
        )

        code_text = await self._call_llm_text(prompt)
        code = self._extract_code_block(code_text)
        self.store.write_text(f"models/{opportunity_id}/code", code, ext=".py")
        logger.info("[Modeler] Code generated (%d lines)", len(code.splitlines()))
        return code
