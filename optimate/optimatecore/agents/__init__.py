"""Lazy agent imports via PEP 562 module __getattr__.

Importing a single agent no longer drags in all agent modules and their
heavy dependencies (pandas, numpy, solver libraries, etc.).
"""

from __future__ import annotations

_AGENT_MAP = {
    "BusinessAnalyst": "optimatecore.agents.business_analyst",
    "DataProfiler": "optimatecore.agents.data_profiler",
    "OpportunityRanker": "optimatecore.agents.opportunity_ranker",
    "Formulator": "optimatecore.agents.formulator",
    "Modeler": "optimatecore.agents.modeler",
    "Executor": "optimatecore.agents.executor",
    "ReportWriter": "optimatecore.agents.report_writer",
    "AssignmentScout": "optimatecore.agents.scouts.assignment_scout",
    "InventoryScout": "optimatecore.agents.scouts.inventory_scout",
    "SchedulingScout": "optimatecore.agents.scouts.scheduling_scout",
}

__all__ = list(_AGENT_MAP)


def __getattr__(name: str):
    if name in _AGENT_MAP:
        import importlib
        module = importlib.import_module(_AGENT_MAP[name])
        obj = getattr(module, name)
        # Cache on this module so subsequent accesses are direct
        globals()[name] = obj
        return obj
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
