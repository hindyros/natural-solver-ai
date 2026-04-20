from abc import ABC, abstractmethod


class BaseSolverTemplate(ABC):
    solver_name: str = ""
    supported_problem_types: list[str] = []

    @abstractmethod
    def skeleton(self) -> str:
        """Return the template skeleton code as a string."""

    def required_imports(self) -> list[str]:
        return []
