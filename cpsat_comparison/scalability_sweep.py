import os
import json
import time
import random
from ortools.sat.python import cp_model

EC2_CONFIG_PATH = "src/simulation/config/ec2_config_virt.json"
PAI_FULL_PATH   = "src/pai_trace/traces/pai_full.json"
OUT_PATH        = "cpsat_comparison/scalability_results.json"

TIME_LIMIT_S    = 1800.0
COST_SCALE      = 100_000
SIZES           = [50, 100, 200, 400, 800]
RANDOM_SEED     = 42

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
    rng = random.Random(seed)
    chosen = sorted(rng.sample(all_ids, n_tasks), key=int)
    tasks = []
    for jid in chosen:
        job = trace[jid]
        tid = next(iter(job["tasks"]))
        demand = job["tasks"][tid]["demand"]["any"]
        tasks.append({"name": f"{job['name']}_{tid}", "demand": demand})
    return tasks

def solve(instance_types, tasks):
    N = len(tasks)
    T = len(instance_types)
    model = cp_model.CpModel()

    x = {(i, j): model.NewBoolVar(f"x_{i}_{j}") for i in range(N) for j in range(N)}
    y = {(j, t): model.NewBoolVar(f"y_{j}_{t}") for j in range(N) for t in range(T)}
    z = [model.NewBoolVar(f"z_{j}") for j in range(N)]

    for i in range(N):
        model.AddExactlyOne(x[i, j] for j in range(N))

    for j in range(N):
        model.Add(sum(y[j, t] for t in range(T)) == z[j])

    for i in range(N):
        for j in range(N):
            model.AddImplication(x[i, j], z[j])

    for j in range(N):
        for r in range(3):
            demand_expr   = sum(tasks[i]["demand"][r] * x[i, j] for i in range(N))
            capacity_expr = sum(
                instance_types[t]["capacity"][r] * y[j, t] for t in range(T)
            )
            model.Add(demand_expr <= capacity_expr)

    for j in range(N - 1):
        model.Add(z[j] >= z[j + 1])

    model.Minimize(
        sum(
            y[j, t] * int(instance_types[t]["cost"] * COST_SCALE)
            for j in range(N)
            for t in range(T)
        )
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = TIME_LIMIT_S
    solver.parameters.log_search_progress = False

    t0     = time.time()
    status = solver.Solve(model)
    elapsed = time.time() - t0

    status_name = solver.StatusName(status)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        cost       = solver.ObjectiveValue() / COST_SCALE
        best_bound = solver.BestObjectiveBound() / COST_SCALE
    else:
        cost       = None
        best_bound = solver.BestObjectiveBound() / COST_SCALE

    return status_name, cost, best_bound, elapsed

def main():
    instance_types = load_instance_types(EC2_CONFIG_PATH)
    
    # Load existing results if any
    results = []
    if os.path.exists(OUT_PATH):
        try:
            with open(OUT_PATH) as f:
                results = json.load(f)
        except Exception:
            results = []

    completed_sizes = {r["n_tasks"] for r in results if r.get("status") in ["OPTIMAL", "FEASIBLE"]}
    
    for n in SIZES:
        if n in completed_sizes:
            print(f"N={n} already completed, skipping.", flush=True)
            continue
            
        print(f"\n{'='*60}", flush=True)
        print(f"Solving for N={n} tasks  (time limit={int(TIME_LIMIT_S/60)} min)...", flush=True)
        tasks = load_tasks(PAI_FULL_PATH, n)
        status, cost, best_bound, elapsed = solve(instance_types, tasks)
        row = {
            "n_tasks":    n,
            "status":     status,
            "cost":       cost,
            "best_bound": best_bound,
            "solve_time": round(elapsed, 2),
        }
        
        # update or append
        results = [r for r in results if r.get("n_tasks") != n]
        results.append(row)
        results.sort(key=lambda x: x["n_tasks"])
        
        print(
            f"N={n}  status={status}  cost={cost}  "
            f"best_bound={best_bound:.4f}  time={elapsed:.1f}s",
            flush=True
        )

        os.makedirs("cpsat_comparison", exist_ok=True)
        with open(OUT_PATH, "w") as f:
            json.dump(results, f, indent=2)
        print(f"Incremental scalability results saved to {OUT_PATH}", flush=True)

if __name__ == "__main__":
    main()
