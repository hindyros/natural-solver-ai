from optimatecore.solvers.templates.base_template import BaseSolverTemplate
from optimatecore.solvers.templates.assignment_pulp import AssignmentPuLPTemplate
from optimatecore.solvers.templates.inventory_pulp import InventoryPuLPTemplate
from optimatecore.solvers.templates.scheduling_ortools import SchedulingORToolsTemplate

_REGISTRY: dict[str, BaseSolverTemplate] = {
    "assignment": AssignmentPuLPTemplate(),
    "linear_assignment": AssignmentPuLPTemplate(),
    "matching": AssignmentPuLPTemplate(),
    "inventory": InventoryPuLPTemplate(),
    "lot_sizing": InventoryPuLPTemplate(),
    "eoq": InventoryPuLPTemplate(),
    "supply_chain": InventoryPuLPTemplate(),
    "scheduling": SchedulingORToolsTemplate(),
    "job_shop": SchedulingORToolsTemplate(),
    "shift_scheduling": SchedulingORToolsTemplate(),
}


class SolverRegistry:
    @staticmethod
    def get_template(scout_type: str, problem_class: str = "") -> BaseSolverTemplate:
        key = scout_type.lower()
        if key in _REGISTRY:
            return _REGISTRY[key]
        # Try problem_class
        key2 = problem_class.lower().replace(" ", "_")
        if key2 in _REGISTRY:
            return _REGISTRY[key2]
        # Default to assignment (most common)
        return AssignmentPuLPTemplate()
