"""
scalability_sweep.py  –  FIXED version using per-type count model
==================================================================
Runs the fixed CP-SAT bin-packing formulation at sizes [50, 100, 200, 400, 800].
Writes incremental results to cpsat_comparison/scalability_results.json.

Changes vs original
--------------------
- Uses the same per-type count reformulation as the fixed cpsat_scheduler.py
- num_search_workers = 8
- log_search_progress = True
- Assertion: best_bound <= objective after every solve
- Warning if best_bound < 0.5 * objective
- Skips already-OPTIMAL rows; re-runs FEASIBLE rows to try to improve
"""

import os
import json
import time
import random
from ortools.sat.python import cp_model

EC2_CONFIG_PATH = "src/simulation/config/ec2_config_virt.json"
PAI_200_PATH    = "src/pai_trace/traces/pai_200.json"
PAI_FULL_PATH   = "src/pai_trace/traces/pai_full.json"
OUT_PATH        = "cpsat_comparison/scalability_results.json"

TIME_LIMIT_S  = 1800.0   # 30 min per size
COST_SCALE    = 100_000
SIZES         = [50, 100, 200, 400, 800]
RANDOM_SEED   = 42
NUM_WORKERS   = 8


# ── Data helpers ──────────────────────────────────────────────────────────────
def load_instance_types(path):
    with open(path) as f:
        cfg = json.load(f)
    types = []
    for name, info in cfg["instance_types"].items():
        types.append({
            "name":     name,
            "capacity": info["capacity"],
            "cost":     info["cost"],
        })
    return types


def load_tasks(path, n_tasks, seed=RANDOM_SEED):
    with open(path) as f:
        trace = json.load(f)
    all_ids = sorted(trace.keys(), key=int)
    if n_tasks > len(all_ids):
        raise ValueError(f"Requested {n_tasks} tasks but trace only has {len(all_ids)}")
    rng    = random.Random(seed)
    chosen = sorted(rng.sample(all_ids, n_tasks), key=int)
    tasks  = []
    for jid in chosen:
        job    = trace[jid]
        tid    = next(iter(job["tasks"]))
        demand = job["tasks"][tid]["demand"]["any"]
        tasks.append({"name": f"{job['name']}_{tid}", "demand": demand})
    return tasks


# ── Per-type count model ──────────────────────────────────────────────────────
def solve(instance_types, tasks, time_limit_s=TIME_LIMIT_S, num_workers=NUM_WORKERS):
    """
    Proper multi-dimensional bin-packing.

    Variables
    ---------
    cnt[t]  IntVar(0, N)  – how many instances of type t to open
    u[i,t]  BoolVar       – task i assigned to some instance of type t

    Capacity constraint (per type, per resource)
    --------------------------------------------
    sum_i demand[i][r] * u[i,t]  <=  capacity[t][r] * cnt[t]

    Objective
    ---------
    minimize  sum_t  cnt[t] * int(cost[t] * COST_SCALE)
    """
    N = len(tasks)
    T = len(instance_types)
    model = cp_model.CpModel()

    # ── Variables ──────────────────────────────────────────────────────────────
    cnt = [model.NewIntVar(0, N, f"cnt_{t}") for t in range(T)]
    u   = {(i, t): model.NewBoolVar(f"u_{i}_{t}")
           for i in range(N) for t in range(T)}

    # ── Infeasibility cuts (task can't fit alone on this type) ─────────────────
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

    # ── Assignment: each task to exactly one type ──────────────────────────────
    for i in range(N):
        model.AddExactlyOne(u[i, t] for t in range(T))

    # ── Capacity: aggregate demand ≤ cnt × capacity ────────────────────────────
    for t in range(T):
        cap = instance_types[t]["capacity"]
        for r in range(3):
            model.Add(
                sum(tasks[i]["demand"][r] * u[i, t] for i in range(N))
                <= cap[r] * cnt[t]
            )

    # ── Implication: if task goes to type t, open ≥1 instance ─────────────────
    for t in range(T):
        for i in range(N):
            model.Add(cnt[t] >= 1).OnlyEnforceIf(u[i, t])

    # ── Objective ──────────────────────────────────────────────────────────────
    cost_coeffs = [int(instance_types[t]["cost"] * COST_SCALE) for t in range(T)]
    model.Minimize(sum(cnt[t] * cost_coeffs[t] for t in range(T)))

    # ── Solve ──────────────────────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers  = num_workers
    solver.parameters.log_search_progress = True

    t0      = time.time()
    status  = solver.Solve(model)
    elapsed = time.time() - t0

    status_name = solver.StatusName(status)
    raw_obj     = solver.ObjectiveValue()
    raw_bound   = solver.BestObjectiveBound()

    print(f"\n--- ResponseStats (N={N}) ---")
    print(solver.ResponseStats())
    print(f"NumBranches:  {solver.NumBranches()}")
    print(f"NumConflicts: {solver.NumConflicts()}")

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        cost       = raw_obj   / COST_SCALE
        best_bound = raw_bound / COST_SCALE

        # ── Scale-mismatch sanity check ────────────────────────────────────────
        print(f"\n--- Scale check (N={N}) ---")
        print(f"  raw_obj={raw_obj:.1f}  scaled_obj={cost:.5f}")
        print(f"  raw_bound={raw_bound:.1f}  scaled_bound={best_bound:.5f}")

        # ── Assertion ──────────────────────────────────────────────────────────
        assert best_bound <= cost + 1e-6, (
            f"ASSERTION FAILED (N={N}): best_bound {best_bound:.5f} > objective {cost:.5f}"
        )
        if best_bound < 0.5 * cost:
            print(
                f"WARNING (N={N}): best_bound ({best_bound:.4f}) < 0.5×objective ({cost:.4f}) "
                f"– bound is still not trustworthy!"
            )
        gap_pct = 100.0 * (cost - best_bound) / cost if cost else 0.0
        print(f"  Gap: {gap_pct:.2f}%  Assertion: PASSED")
    else:
        cost       = None
        best_bound = raw_bound / COST_SCALE

    return status_name, cost, best_bound, elapsed


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    instance_types = load_instance_types(EC2_CONFIG_PATH)

    # Load existing results; skip only OPTIMAL ones
    results = []
    if os.path.exists(OUT_PATH):
        try:
            with open(OUT_PATH) as f:
                results = json.load(f)
        except Exception:
            results = []

    completed_optimal = {r["n_tasks"] for r in results if r.get("status") == "OPTIMAL"}

    for n in SIZES:
        if n in completed_optimal:
            print(f"N={n} already OPTIMAL, skipping.", flush=True)
            continue

        print(f"\n{'='*60}", flush=True)
        print(f"Solving N={n} tasks  (time_limit={int(TIME_LIMIT_S/60)} min, "
              f"workers={NUM_WORKERS})", flush=True)

        try:
            # Use pai_full.json for all sizes (it has 800+ tasks)
            tasks = load_tasks(PAI_FULL_PATH, n)
        except ValueError as e:
            print(f"ERROR loading tasks for N={n}: {e}", flush=True)
            continue

        status, cost, best_bound, elapsed = solve(instance_types, tasks)

        row = {
            "n_tasks":    n,
            "status":     status,
            "cost":       cost,
            "best_bound": best_bound,
            "solve_time": round(elapsed, 2),
        }

        print(
            f"\nN={n}  status={status}  cost={cost}  "
            f"best_bound={best_bound:.5f}  time={elapsed:.1f}s",
            flush=True,
        )

        # Update results list and save incrementally
        results = [r for r in results if r.get("n_tasks") != n]
        results.append(row)
        results.sort(key=lambda x: x["n_tasks"])

        os.makedirs("cpsat_comparison", exist_ok=True)
        with open(OUT_PATH, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Saved incremental results → {OUT_PATH}", flush=True)


if __name__ == "__main__":
    main()
