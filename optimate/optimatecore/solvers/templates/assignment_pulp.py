from optimatecore.solvers.templates.base_template import BaseSolverTemplate


class AssignmentPuLPTemplate(BaseSolverTemplate):
    solver_name = "pulp"
    supported_problem_types = ["assignment", "linear_assignment", "matching"]

    def skeleton(self) -> str:
        return '''import json
import pulp

with open("data.json") as f:
    data = json.load(f)

# --- DATA SETUP ---
# TODO: Extract the two entity sets and cost/preference matrix from data.
# Example:
#   workers = data["workers"]          # list of worker IDs
#   shifts = data["shifts"]            # list of shift IDs
#   cost = data["cost_matrix"]         # dict or 2D list: cost[i][j]

# --- MODEL ---
prob = pulp.LpProblem("AssignmentProblem", pulp.LpMinimize)  # change to LpMaximize if needed

# --- DECISION VARIABLES ---
# x[i][j] = 1 if entity_i is assigned to entity_j, 0 otherwise
# TODO: Replace 'workers' and 'shifts' with actual entity names from data
x = pulp.LpVariable.dicts(
    "assign",
    [(i, j) for i in workers for j in shifts],
    cat="Binary",
)

# --- OBJECTIVE ---
# TODO: Replace with actual cost expression using the data
prob += pulp.lpSum(
    cost[i][j] * x[i, j]
    for i in workers
    for j in shifts
)

# --- CONSTRAINTS ---
# Each entity from set 1 assigned to at most one entity from set 2
for i in workers:
    prob += pulp.lpSum(x[i, j] for j in shifts) <= 1, f"one_per_worker_{i}"

# Each entity from set 2 covered by exactly one entity from set 1
for j in shifts:
    prob += pulp.lpSum(x[i, j] for i in workers) == 1, f"cover_shift_{j}"

# TODO: Add any additional constraints from the formulation

# --- SOLVE ---
prob.solve(pulp.PULP_CBC_CMD(msg=0))

# --- OUTPUT ---
status = pulp.LpStatus[prob.status]
obj_val = pulp.value(prob.objective) if prob.status == 1 else None
print(f"OBJECTIVE_VALUE: {obj_val}")

solution = {
    "status": status,
    "objective": obj_val,
    "variables": {
        f"x_{i}_{j}": int(round(pulp.value(x[i, j]) or 0))
        for i in workers
        for j in shifts
        if pulp.value(x[i, j]) and pulp.value(x[i, j]) > 0.5
    },
}

with open("solution_output.json", "w") as f:
    json.dump(solution, f, indent=2)
'''
