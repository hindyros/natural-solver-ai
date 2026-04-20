from optimatecore.solvers.templates.base_template import BaseSolverTemplate


class InventoryPuLPTemplate(BaseSolverTemplate):
    solver_name = "pulp"
    supported_problem_types = ["inventory", "lot_sizing", "eoq", "supply_chain"]

    def skeleton(self) -> str:
        return '''import json
import pulp

with open("data.json") as f:
    data = json.load(f)

# --- DATA SETUP ---
# TODO: Extract inventory parameters from data.
# Example keys to look for:
#   T = number of planning periods
#   demand = data["demand"]              # list of demand[t] for t in range(T)
#   holding_cost = data["holding_cost"]  # cost per unit per period
#   ordering_cost = data["ordering_cost"]# fixed cost per order
#   initial_inventory = data.get("initial_inventory", 0)
#   max_inventory = data.get("max_inventory", float("inf"))

T = len(demand)
periods = range(T)

# --- MODEL ---
prob = pulp.LpProblem("InventoryOptimization", pulp.LpMinimize)

# --- DECISION VARIABLES ---
order = pulp.LpVariable.dicts("order", periods, lowBound=0)        # units ordered in period t
inventory = pulp.LpVariable.dicts("inventory", periods, lowBound=0) # inventory at end of period t
y = pulp.LpVariable.dicts("y", periods, cat="Binary")               # 1 if order placed in period t

# --- OBJECTIVE: minimize total holding + ordering cost ---
prob += (
    pulp.lpSum(holding_cost * inventory[t] for t in periods)
    + pulp.lpSum(ordering_cost * y[t] for t in periods)
)

# --- CONSTRAINTS ---
# Inventory balance
for t in periods:
    if t == 0:
        prob += inventory[t] == initial_inventory + order[t] - demand[t], f"balance_0"
    else:
        prob += inventory[t] == inventory[t - 1] + order[t] - demand[t], f"balance_{t}"

# Storage capacity
if max_inventory < float("inf"):
    for t in periods:
        prob += inventory[t] <= max_inventory, f"capacity_{t}"

# Big-M: can only order if y[t]=1
M = sum(demand) + 1
for t in periods:
    prob += order[t] <= M * y[t], f"bigm_{t}"

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
        "orders": {str(t): pulp.value(order[t]) for t in periods},
        "inventory_levels": {str(t): pulp.value(inventory[t]) for t in periods},
        "order_placed": {str(t): int(round(pulp.value(y[t]) or 0)) for t in periods},
    },
}

with open("solution_output.json", "w") as f:
    json.dump(solution, f, indent=2)
'''
