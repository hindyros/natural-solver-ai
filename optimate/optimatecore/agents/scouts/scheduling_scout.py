from optimatecore.agents.scouts.base_scout import BaseScout


class SchedulingScout(BaseScout):
    agent_name = "SchedulingScout"
    scout_type = "scheduling"
    domain_keywords = [
        "schedule", "shift", "timeline", "deadline", "precedence",
        "machine", "job", "calendar", "time slots", "crew", "gantt",
        "makespan", "tardiness", "due date",
    ]
    system_prompt = (
        "You are an expert in scheduling and timetabling optimization. "
        "You specialize in detecting opportunities where activities must be assigned "
        "to time slots subject to resource and sequencing constraints: job-shop scheduling, "
        "shift scheduling, project scheduling, machine timetabling. "
        "Always respond with valid JSON."
    )

    def _scout_context(self) -> str:
        return (
            "You are scouting for SCHEDULING optimization opportunities.\n\n"
            "Scheduling problems involve assigning activities to time slots while "
            "respecting resource capacities, deadlines, and sequencing constraints.\n\n"
            "SIGNAL PATTERNS TO LOOK FOR:\n"
            "- Activities/jobs with durations or processing times\n"
            "- Resources (machines, workers, rooms) with limited capacity\n"
            "- Deadlines or due dates for activities\n"
            "- Precedence constraints (job A must finish before job B starts)\n"
            "- Time windows or availability calendars\n"
            "- Shift start/end times and coverage requirements\n\n"
            "CLASSIC EXAMPLES:\n"
            "- Job-shop scheduling minimizing makespan\n"
            "- Nurse/staff shift scheduling\n"
            "- Machine timetabling with maintenance windows\n"
            "- Project scheduling with resource leveling\n\n"
            "HIGH CONFIDENCE signals: columns for start time, end time, duration, "
            "deadline, or resource ID; keywords like 'schedule', 'makespan', 'deadline', "
            "'shift', or 'timeline' in the problem description.\n"
        )
