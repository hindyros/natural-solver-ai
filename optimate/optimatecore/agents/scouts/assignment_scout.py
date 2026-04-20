from optimatecore.agents.scouts.base_scout import BaseScout


class AssignmentScout(BaseScout):
    agent_name = "AssignmentScout"
    scout_type = "assignment"
    domain_keywords = [
        "workers", "shifts", "tasks", "jobs", "routes", "vehicles",
        "resources", "allocation", "assignment", "matching", "pairing",
    ]
    system_prompt = (
        "You are an expert in assignment and matching optimization problems. "
        "You specialize in detecting opportunities where items from one set need to be "
        "matched to items from another set — workers to shifts, vehicles to routes, "
        "tasks to machines. "
        "You are looking at a client's dataset to find if such a structure exists. "
        "Always respond with valid JSON."
    )

    def _scout_context(self) -> str:
        return (
            "You are scouting for ASSIGNMENT optimization opportunities.\n\n"
            "Assignment problems involve matching items from one set to items from another set "
            "to minimize cost or maximize utility.\n\n"
            "SIGNAL PATTERNS TO LOOK FOR:\n"
            "- Two distinct entity types that need to be paired (workers+shifts, vehicles+routes, tasks+agents)\n"
            "- A cost, preference, or efficiency value for each possible pairing\n"
            "- Constraints on how many assignments each entity can take\n"
            "- Coverage requirements (every shift must be filled, every task must be assigned)\n\n"
            "CLASSIC EXAMPLES:\n"
            "- Worker-shift assignment with skill/preference costs\n"
            "- Vehicle-route assignment minimizing total distance\n"
            "- Task-machine assignment minimizing makespan\n"
            "- Student-project assignment with preference scores\n\n"
            "HIGH CONFIDENCE signals: two ID columns that look like they represent different entity types, "
            "a numeric column that could be a cost or preference matrix, and mention of 'assignment', "
            "'allocation', or 'matching' in the problem description.\n"
        )
