from optimatecore.solvers.templates.base_template import BaseSolverTemplate


class SchedulingORToolsTemplate(BaseSolverTemplate):
    solver_name = "ortools"
    supported_problem_types = ["scheduling", "job_shop", "shift_scheduling", "cp_sat"]

    def skeleton(self) -> str:
        return '''import json
from ortools.sat.python import cp_model

with open("data.json") as f:
    data = json.load(f)

# --- DATA SETUP ---
# TODO: Extract scheduling parameters from data.
# Example:
#   jobs = data["jobs"]                         # list of job IDs
#   machines = data.get("machines", ["m0"])     # list of machine IDs
#   processing_time = data["processing_time"]   # dict: processing_time[job_id] = int duration
#   deadlines = data.get("deadlines", {})       # dict: deadlines[job_id] = int deadline

# Horizon: upper bound on total schedule length
horizon = sum(processing_time.values()) + max(processing_time.values(), default=0)

# --- MODEL ---
model = cp_model.CpModel()

# --- DECISION VARIABLES ---
start = {}
end = {}
interval = {}

for j in jobs:
    duration = int(processing_time[j])
    start[j] = model.NewIntVar(0, horizon, f"start_{j}")
    end[j] = model.NewIntVar(0, horizon, f"end_{j}")
    interval[j] = model.NewIntervalVar(start[j], duration, end[j], f"interval_{j}")

# --- CONSTRAINTS ---
# No-overlap on each machine (group jobs by machine if applicable)
# TODO: If jobs are assigned to specific machines, group accordingly
model.AddNoOverlap(list(interval.values()))

# Meet deadlines
for j in jobs:
    if j in deadlines:
        model.Add(end[j] <= int(deadlines[j]))

# TODO: Add precedence constraints if applicable

# --- OBJECTIVE: minimize makespan ---
makespan = model.NewIntVar(0, horizon, "makespan")
model.AddMaxEquality(makespan, [end[j] for j in jobs])
model.Minimize(makespan)

# --- SOLVE ---
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = 30.0
status_code = solver.Solve(model)
status_str = solver.StatusName(status_code)

obj_val = None
variable_values = {}

if status_code in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    obj_val = solver.ObjectiveValue()
    variable_values = {
        "start_times": {j: solver.Value(start[j]) for j in jobs},
        "end_times": {j: solver.Value(end[j]) for j in jobs},
    }

print(f"OBJECTIVE_VALUE: {obj_val}")

solution = {
    "status": status_str,
    "objective": obj_val,
    "variables": variable_values,
}

with open("solution_output.json", "w") as f:
    json.dump(solution, f, indent=2)
'''
