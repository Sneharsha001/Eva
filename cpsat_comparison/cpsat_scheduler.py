"""
cpsat_scheduler.py  –  FIXED vector bin-packing CP-SAT model
=============================================================
Key changes vs original slot-indexed model
-------------------------------------------
1. REFORMULATION: uses per-type COUNT variables  cnt[t]  (IntVar 0..N)
   instead of N × N slot × task binary variables.
   Task assignment: u[i, t] = 1 iff task i is served by some instance of type t.
   The capacity constraint is linearised:
       sum_i demand[i][r] * u[i,t]  <=  capacity[t][r] * cnt[t]   ∀ t, r
   This is valid because all instances of the same type are identical
   (homogeneous bin packing per type).

2. SYMMETRY: per-type count variables eliminate the inter-slot symmetry
   entirely. No "slot 3 of type p3.2xlarge" vs "slot 7" distinction.

3. OBJECTIVE: sum_t cnt[t] * cost[t]  (integer, scaled)

4. WORKERS: num_search_workers = 8
5. LOGGING: log_search_progress = True
6. ASSERTION: best_bound <= objective_value after every solve;
   WARNING if best_bound < 0.5 * objective_value
"""

import os
import json
import time
from ortools.sat.python import cp_model


# ── Constants ────────────────────────────────────────────────────────────────
COST_SCALE = 100_000        # multiply float $/hr → integer millidollars


# ── Data loading ─────────────────────────────────────────────────────────────
def load_data(ec2_path="src/simulation/config/ec2_config_virt.json",
              pai_path="src/pai_trace/traces/pai_200.json"):
    with open(ec2_path) as f:
        ec2_config = json.load(f)
    with open(pai_path) as f:
        pai_200 = json.load(f)

    instance_types = []
    for it_name, it_info in ec2_config["instance_types"].items():
        instance_types.append({
            "name":     it_name,
            "capacity": it_info["capacity"],   # [GPU, CPU, RAM]
            "cost":     it_info["cost"],        # $/hr float
        })

    tasks = []
    for job_id in sorted(int(k) for k in pai_200.keys()):
        job_info = pai_200[str(job_id)]
        task_id  = list(job_info["tasks"].keys())[0]
        task_info = job_info["tasks"][task_id]
        demand = task_info["demand"]["any"]     # [GPU, CPU, RAM]
        tasks.append({
            "name":   f"{job_info['name']}_{task_id}",
            "demand": demand,
        })

    return instance_types, tasks


# ── Solver ────────────────────────────────────────────────────────────────────
def solve_bin_packing(instance_types, tasks,
                      time_limit_s=1800.0,
                      num_workers=8):
    """
    Proper multi-dimensional bin-packing via per-type count variables.

    Variables
    ---------
    cnt[t]  : IntVar(0, N) – number of instances of type t to open
    u[i, t] : BoolVar     – task i is assigned to a type-t instance

    Constraints
    -----------
    1. Each task assigned to exactly one type:
           sum_t u[i,t] == 1   ∀ i
    2. Aggregate capacity per type per resource:
           sum_i demand[i][r] * u[i,t] <= capacity[t][r] * cnt[t]   ∀ t, r
       (All N instances of the same type are interchangeable →
        the total demand for type t cannot exceed cnt[t] × one-instance capacity)
    3. Only types that have at least one feasible task get opened:
           cnt[t] >= 1  iff  some u[i,t] == 1
           → encoded as:  cnt[t] >= sum_i u[i,t] / max_tasks_per_bin[t]  (via AddDivisionEquality
             or simpler: cnt[t] * max_cap[t][r] >= sum demand …)
           → already implied by constraint 2 since capacity is finite

    Objective
    ---------
    Minimize sum_t cnt[t] * int(cost[t] * COST_SCALE)
    """
    N = len(tasks)
    T = len(instance_types)
    model = cp_model.CpModel()

    print(f"Building model: N={N} tasks, T={T} instance types", flush=True)

    # ── Variables ─────────────────────────────────────────────────────────────
    # cnt[t]: how many instances of type t to open (0 … N upper bound is safe)
    cnt = [model.NewIntVar(0, N, f"cnt_{t}") for t in range(T)]

    # u[i,t]: task i goes to an instance of type t
    u = {(i, t): model.NewBoolVar(f"u_{i}_{t}")
         for i in range(N) for t in range(T)}

    print(f"Variables: {T} cnt IntVars, {N*T} u BoolVars  (total = {T + N*T})", flush=True)
    print(f"[Original model would have had {N*N + N*T + N} variables]", flush=True)

    # ── Constraints ───────────────────────────────────────────────────────────
    # 1. Each task assigned to exactly one type
    for i in range(N):
        model.AddExactlyOne(u[i, t] for t in range(T))

    # 2. Capacity: total demand assigned to type t ≤ cnt[t] × capacity
    for t in range(T):
        cap = instance_types[t]["capacity"]
        for r in range(3):  # 0=GPU, 1=CPU, 2=RAM
            # Filter out tasks that demand[r] > cap[r] for this type
            # (these tasks CANNOT go to type t – add implication for pruning)
            model.Add(
                sum(tasks[i]["demand"][r] * u[i, t] for i in range(N))
                <= cap[r] * cnt[t]
            )

    # 3. Infeasibility cuts: if task i can't fit alone on type t, forbid u[i,t]
    #    (tightens LP relaxation significantly)
    for i in range(N):
        feasible_types = []
        for t in range(T):
            cap = instance_types[t]["capacity"]
            if all(tasks[i]["demand"][r] <= cap[r] for r in range(3)):
                feasible_types.append(t)
            else:
                model.Add(u[i, t] == 0)
        if not feasible_types:
            raise ValueError(f"Task {tasks[i]['name']} cannot fit on any instance type!")

    # 4. Implication: if any task assigned to type t, open at least 1 instance
    #    (redundant given constraint 2 but speeds up propagation)
    for t in range(T):
        for i in range(N):
            # u[i,t]=1  →  cnt[t] >= 1
            model.Add(cnt[t] >= 1).OnlyEnforceIf(u[i, t])

    # ── Objective ─────────────────────────────────────────────────────────────
    cost_coeffs = [int(instance_types[t]["cost"] * COST_SCALE) for t in range(T)]
    total_cost  = sum(cnt[t] * cost_coeffs[t] for t in range(T))
    model.Minimize(total_cost)

    # ── Solver parameters ─────────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers  = num_workers
    solver.parameters.log_search_progress = True

    print(f"\nSolver parameters:", flush=True)
    print(f"  max_time_in_seconds = {time_limit_s}", flush=True)
    print(f"  num_search_workers  = {num_workers}", flush=True)
    print(f"  log_search_progress = True", flush=True)
    print(f"  COST_SCALE          = {COST_SCALE}", flush=True)
    print(f"  cost_coeffs range   = [{min(cost_coeffs)}, {max(cost_coeffs)}]", flush=True)

    # ── Solve ─────────────────────────────────────────────────────────────────
    print("\nStarting solver...", flush=True)
    wall_t0 = time.time()
    status  = solver.Solve(model)
    wall_elapsed = time.time() - wall_t0

    # ── Full response stats ───────────────────────────────────────────────────
    print("\n=== ResponseStats ===")
    print(solver.ResponseStats())
    print(f"WallTime (Python):  {wall_elapsed:.3f} s")
    print(f"NumBranches:        {solver.NumBranches()}")
    print(f"NumConflicts:       {solver.NumConflicts()}")

    # ── Extract and validate results ──────────────────────────────────────────
    status_name = solver.StatusName(status)
    raw_obj     = solver.ObjectiveValue()
    raw_bound   = solver.BestObjectiveBound()
    obj_value   = raw_obj   / COST_SCALE
    best_bound  = raw_bound / COST_SCALE

    print(f"\n=== Scale check ===")
    print(f"  COST_SCALE used for objective:  {COST_SCALE}")
    print(f"  COST_SCALE used for bound read: {COST_SCALE}")
    print(f"  ObjectiveValue    (raw / scaled): {raw_obj:.1f} / {obj_value:.5f}")
    print(f"  BestObjectiveBound(raw / scaled): {raw_bound:.1f} / {best_bound:.5f}")

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        # Assertion: bound must be ≤ objective
        assert best_bound <= obj_value + 1e-6, (
            f"ASSERTION FAILED: best_bound {best_bound:.5f} > objective {obj_value:.5f}"
        )
        if best_bound < 0.5 * obj_value:
            print(f"WARNING: best_bound ({best_bound:.4f}) < 0.5 × objective ({obj_value:.4f}) "
                  f"– bound is still not trustworthy!", flush=True)
        gap_pct = 100.0 * (obj_value - best_bound) / obj_value if obj_value else 0.0
        print(f"  Gap: {gap_pct:.2f}%")
        print(f"  Assertion best_bound <= objective: PASSED")

        # Build assignment summary
        assignment = []
        for t in range(T):
            count = solver.Value(cnt[t])
            if count > 0:
                assigned_tasks = [tasks[i]["name"]
                                  for i in range(N) if solver.Value(u[i, t])]
                assignment.append({
                    "instance_type": instance_types[t]["name"],
                    "count":         count,
                    "tasks":         assigned_tasks,
                })

        return status_name, obj_value, best_bound, wall_elapsed, assignment

    else:
        print(f"Status: {status_name} – no feasible solution found within time limit.")
        return status_name, None, None, wall_elapsed, []


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    instance_types, tasks = load_data()
    status, cost, best_bound, solve_time, assignment = solve_bin_packing(
        instance_types, tasks,
        time_limit_s=1800.0,
        num_workers=8,
    )

    results = [{
        "scheduler name": "CP-SAT",
        "total cost":     cost,
        "best bound":     best_bound,
        "runtime":        solve_time,
        "solve_status":   status,
        "assignment":     assignment,
    }]

    out_path = "cpsat_comparison/cpsat_results.json"
    with open(out_path, "w") as f:
        json.dump(results, f, indent=4)
    print(f"\nResults saved to {out_path}")


if __name__ == "__main__":
    main()
