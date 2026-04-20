# Problem 9 — Multi-Objective Job Scheduling (MOOP)

**Difficulty:** Hard
**Type:** Multi-Objective Optimization Problem (MOOP)
**Datasets:** `data/jobs.csv`, `data/machines.csv`, `data/setup_times.csv`

---

## Context

A semiconductor fab must schedule **20 jobs** across **4 machines**. Each job has a
processing time on each machine, a due date, and a weight (priority). The goal is to
simultaneously minimize **three competing objectives**:

1. **Total weighted tardiness** (primary quality metric)
2. **Makespan** (total completion time)
3. **Total setup cost** (sequence-dependent setup times between jobs)

This is a **multi-objective flexible job shop scheduling problem (MO-FJSSP)**.
Use NSGA-II to approximate the Pareto frontier.

---

## Data Description

### `jobs.csv`
| Column | Description |
|--------|-------------|
| job_id | Job identifier (J01–J20) |
| weight | Priority weight (1=low, 5=high) |
| due_date | Due date in time units from start |
| proc_time_M1..M4 | Processing time on each machine (time units) |
| eligible_machines | Comma-separated list of machines that can process the job |

### `machines.csv`
| Column | Description |
|--------|-------------|
| machine_id | Machine ID (M1–M4) |
| speed_factor | Relative speed (1.0 = baseline) |
| max_jobs | Maximum jobs schedulable |

### `setup_times.csv`
20×20 matrix: setup_times[i][j] = time to switch from job i to job j on the same machine.

---

## Mathematical Formulation

**Decision variables:**
- σ_m = permutation (sequence) of jobs assigned to machine m
- C_{j,m} = completion time of job j on machine m

**Objective functions:**
f1 = Σ_j w_j · max(0, C_j - d_j)   (weighted tardiness)
f2 = max_j C_j                       (makespan)
f3 = Σ_{consecutive j,k on same machine} setup[j][k]   (total setup cost)

**Constraints:**
- Each job assigned to exactly one eligible machine
- No two jobs overlap on the same machine
- Setup time respected between consecutive jobs

**Approach:** NSGA-II with chromosome = machine assignment + job ordering per machine.

---

## Questions to Answer

1. Plot the 3D Pareto frontier (f1, f2, f3).
2. Which solution on the frontier has the best tardiness-makespan trade-off?
3. How many non-dominated solutions exist in the population after 200 generations?
4. What is the hypervolume indicator of the Pareto front?
5. If Job J07 (weight=5) must be completed by its due date, how does the frontier shift?
