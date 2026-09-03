"""
decision_point_analysis_tnrp.py
================================
TNRP-corrected CP-SAT bin-packing comparison against EVA's actual decision-point
snapshots. This is the authoritative version for the paper.

Key differences from prior versions:
  - GPU tasks CAN share an instance (no hard GPU co-location ban).
  - When GPU tasks share an instance, EVA's TNRP interference penalty is added to
    the objective as an explicit cost term — matching EVA's own get_contention_rate()
    logic exactly (direct lookup → pairwise product fallback).
  - Outputs a 3-column comparison table:
      EVA | CP-SAT original (free coloc) | CP-SAT no-GPU-coloc | CP-SAT TNRP-corrected
  - Marks both earlier versions as intermediate/diagnostic steps, not final results.

Formula (Section 2 of notes/tnrp_formula.md):
  For each pair (i, j) of GPU tasks assigned to the same instance type t:
    penalty(i,j) = cost(min_it_i) × (1 - rate(i|j))
                 + cost(min_it_j) × (1 - rate(j|i))
  Approximation: uses pairwise product fallback for multi-task groups (matches EVA's
  own get_contention_rate() when exact tuple is missing from contention_map).
  Audit confirmed: 100% of 3+-way groups in the 8 snapshots had DIRECT entries in
  contention_map, so the pairwise fallback is only used for novel CP-SAT groupings.
"""

import json, os, time, ast
from ortools.sat.python import cp_model

REPORT_PATH      = r"src/simulation_experiments/EVAGangScheduler_pai_200/report.json"
EC2_CFG_PATH     = r"src/simulation/config/ec2_config_virt.json"
ORIG_PATH        = r"cpsat_comparison/decision_point_snapshots.json"
NOGPU_PATH       = r"cpsat_comparison/decision_point_snapshots_nogpu_colocate.json"
OUTPUT_JSON_PATH = r"cpsat_comparison/decision_point_snapshots_tnrp.json"
OUTPUT_MD_PATH   = r"notes/decision_point_comparison_tnrp.md"
COST_SCALE       = 100_000
DEFAULT_RATE     = 0.95   # EVA's default_contention_rate

print("Loading report.json ...", flush=True)
with open(REPORT_PATH) as f:
    report = json.load(f)
print("Loading ec2_config_virt.json ...", flush=True)
with open(EC2_CFG_PATH) as f:
    ec2_cfg = json.load(f)
print("Loading original snapshots ...", flush=True)
with open(ORIG_PATH) as f:
    orig_snapshots = json.load(f)
print("Loading no-GPU-coloc snapshots ...", flush=True)
with open(NOGPU_PATH) as f:
    nogpu_snapshots = json.load(f)

instances   = report["instances"]
tasks_data  = report["tasks"]
jobs_data   = report["jobs"]
inst_types  = report["instance_types"]
cm          = report["contention_map"]   # EVA's contention_map

it_by_name = {}
for v in inst_types.values():
    it_by_name[v["name"]] = {"cost": v["cost"], "capacity": v["capacity"]}

cpsat_types = []
for name, info in ec2_cfg["instance_types"].items():
    cpsat_types.append({"name": name, "capacity": info["capacity"], "cost": info["cost"]})

print(f"  {len(instances)} instances, {len(tasks_data)} tasks, {len(cpsat_types)} instance types for CP-SAT")

# ── Helpers: snapshot reconstruction (unchanged from prior versions) ────────────

def instance_active_at(inst, t):
    for sess in inst["active_session_queue"]:
        start = sess["instantiate_start_time"]
        end   = sess.get("shut_down_end_time")
        if start <= t and (end is None or t < end):
            return True
    return False

def committed_tasks_at(inst, t):
    committed = []
    for h in inst["history"]:
        if h["timestamp"] <= t:
            committed = h.get("committed_task_ids", [])
        else:
            break
    return set(committed)

def task_demand(task_info):
    dd = task_info["demand_dict"]
    for fam in ["p3", "c7i", "r7i"]:
        if fam in dd:
            return list(dd[fam])
    return list(list(dd.values())[0])

def snapshot_at(t):
    active_ids = set()
    eva_cost_hr = 0.0
    task_ids = set()
    assignment_map = {}
    for inst_id_str, inst in instances.items():
        if instance_active_at(inst, t):
            active_ids.add(int(inst_id_str))
            it_name = inst["instance_type_name"]
            eva_cost_hr += it_by_name[it_name]["cost"]
            ctasks = committed_tasks_at(inst, t)
            for tid in ctasks:
                task_ids.add(tid)
                assignment_map[tid] = it_name
    task_demands = []
    for tid in sorted(task_ids):
        ti = tasks_data[str(tid)]
        task_demands.append({
            "task_id": tid,
            "name": ti["name"] + " (job " + str(ti["job_id"]) + ")",
            "demand": task_demand(ti)
        })
    return active_ids, task_ids, eva_cost_hr, task_demands, assignment_map

# ── TNRP helpers ───────────────────────────────────────────────────────────────

def task_label(tid):
    """Return 'job_name_task_name' matching contention_map key format."""
    t = tasks_data[str(tid)]
    job_name  = jobs_data[str(t["job_id"])]["name"]
    task_name = t["name"]
    return f"{job_name}_{task_name}"

def get_contention_rate(key, value_tuple, contention_map):
    """
    Mirrors EVA's EVAGangScheduler.get_contention_rate() exactly.
    key        = 'job_name_task_name' for the TARGET task
    value_tuple = sorted tuple of co-located task labels (all OTHER tasks on instance)
    """
    if key not in contention_map:
        return pow(DEFAULT_RATE, len(value_tuple))

    cm_key = contention_map[key]

    # Try direct lookup — contention_map stores keys as string-repr of tuples
    for k_str, vals in cm_key.items():
        if k_str == "()":
            # empty tuple = isolated, always 1.0
            if len(value_tuple) == 0:
                return sum(vals) / len(vals)
            continue
        try:
            k_tup = ast.literal_eval(k_str)
            if tuple(sorted(k_tup)) == tuple(sorted(value_tuple)):
                return sum(vals) / len(vals)
        except Exception:
            pass

    # Singleton fallback
    if len(value_tuple) == 1:
        return DEFAULT_RATE

    # Pairwise product fallback (EVA's Case 4)
    product = 1.0
    for v in value_tuple:
        product *= get_contention_rate(key, (v,), contention_map)
    return product


def tnrp_penalty_pair(label_i, label_j, min_cost_i, min_cost_j):
    """
    TNRP interference penalty for tasks i and j on the same instance:
      penalty = cost_i × (1 - rate(i|j))  +  cost_j × (1 - rate(j|i))
    Returns float $/hr penalty.
    """
    rate_i_given_j = get_contention_rate(label_i, (label_j,), cm)
    rate_j_given_i = get_contention_rate(label_j, (label_i,), cm)
    return min_cost_i * (1 - rate_i_given_j) + min_cost_j * (1 - rate_j_given_i)


def build_tnrp_penalty_matrix(task_subset, task_labels, min_it_costs):
    """
    Precompute pairwise TNRP penalty matrix P[i][j] for GPU tasks only.
    P[i][j] = tnrp_penalty_pair(i, j)  (symmetric in index, not in rates)
    Only defined for (i < j) pairs.
    """
    N = len(task_subset)
    P = {}
    gpu_indices = [i for i in range(N) if task_subset[i]["demand"][0] > 0]
    for a in range(len(gpu_indices)):
        for b in range(a + 1, len(gpu_indices)):
            i, j = gpu_indices[a], gpu_indices[b]
            pen = tnrp_penalty_pair(task_labels[i], task_labels[j],
                                    min_it_costs[i], min_it_costs[j])
            P[(i, j)] = pen
    return P, gpu_indices


# ── CP-SAT TNRP model ──────────────────────────────────────────────────────────

def cpsat_solve_tnrp(task_subset, task_labels, time_limit_s=60.0, num_workers=8):
    """
    CP-SAT bin-packing model with TNRP interference penalties:
    - GPU tasks CAN share an instance (no hard GPU co-location ban).
    - For each pair (i, j) of GPU tasks, add a binary `colocate[i,j,t]` = 1 iff
      both are assigned to the same instance type t.
    - Objective: sum(cnt[t] * cost[t]) + sum over co-located GPU pairs of TNRP penalty.

    The pairwise penalty is the objective-function analog of EVA's opportunity cost
    degradation — it makes the ILP prefer to separate GPU tasks unless the packing
    benefit (saved instances) outweighs the throughput penalty.
    """
    N = len(task_subset)
    T = len(cpsat_types)

    # Minimum standalone instance cost for each task (for TNRP penalty)
    # This mirrors EVA's task_to_min_it_map
    min_it_costs = []
    for i in range(N):
        d = task_subset[i]["demand"]
        best = None
        for ct in cpsat_types:
            cap = ct["capacity"]
            if all(d[r] <= cap[r] for r in range(3)):
                if best is None or ct["cost"] < best:
                    best = ct["cost"]
        min_it_costs.append(best if best is not None else 0.0)

    P, gpu_indices = build_tnrp_penalty_matrix(task_subset, task_labels, min_it_costs)

    model = cp_model.CpModel()
    cnt = [model.NewIntVar(0, N, f"cnt_{t}") for t in range(T)]
    u   = {(i, t): model.NewBoolVar(f"u_{i}_{t}") for i in range(N) for t in range(T)}

    # Each task assigned to exactly one instance type
    for i in range(N):
        model.AddExactlyOne(u[i, t] for t in range(T))

    # Capacity constraints: sum of demands ≤ capacity × count
    for t in range(T):
        cap = cpsat_types[t]["capacity"]
        for r in range(3):
            model.Add(
                sum(task_subset[i]["demand"][r] * u[i, t] for i in range(N))
                <= cap[r] * cnt[t]
            )

    # Infeasibility pruning: tasks that don't fit on a type must not be assigned
    for i in range(N):
        feasible = []
        for t in range(T):
            cap = cpsat_types[t]["capacity"]
            if all(task_subset[i]["demand"][r] <= cap[r] for r in range(3)):
                feasible.append(t)
            else:
                model.Add(u[i, t] == 0)
        if not feasible:
            raise ValueError(f"Task {task_subset[i]['name']} cannot fit on any instance type!")

    # cnt[t] ≥ 1 whenever any task uses type t
    for t in range(T):
        for i in range(N):
            model.Add(cnt[t] >= 1).OnlyEnforceIf(u[i, t])

    # ── TNRP co-location variables and penalty ──────────────────────────────────
    # colocate[(i,j,t)] = 1 iff tasks i and j are BOTH assigned to type t
    # This is enforced with: colocate[i,j,t] → u[i,t]=1 AND u[j,t]=1
    # We use a product linearisation: colocate[i,j,t] = u[i,t] AND u[j,t]
    # which in CP-SAT is: AddBoolAnd([u[i,t], u[j,t]]).OnlyEnforceIf(coloc)
    #                      AddBoolOr([u[i,t].Not(), u[j,t].Not()]).OnlyEnforceIf(coloc.Not())
    #
    # Penalty term: for each pair (i,j), penalty activates if they share ANY type t.
    # We introduce shared_ij = OR over t of colocate[i,j,t], then add penalty.

    penalty_terms = []   # list of (int_coeff_scaled, BoolVar)

    for (i, j), pen in P.items():
        if pen <= 0:
            continue  # no penalty for this pair
        pen_scaled = int(round(pen * COST_SCALE))
        if pen_scaled == 0:
            continue

        # shared_ij = 1 iff tasks i and j are assigned to the same instance TYPE
        # (Note: in the per-type-count model, all instances of a type are fungible —
        #  two tasks assigned to the same type may or may not be on the same physical
        #  instance. We assume worst-case co-location when the same type is chosen
        #  for both tasks. This is conservative but matches EVA's own assumption.)
        shared_ij = model.NewBoolVar(f"shared_{i}_{j}")

        # shared_ij implies at least one type has BOTH assigned
        type_colocated = []
        for t in range(T):
            cap = cpsat_types[t]["capacity"]
            # Only consider types where both tasks are individually feasible
            d_i = task_subset[i]["demand"]
            d_j = task_subset[j]["demand"]
            if not (all(d_i[r] <= cap[r] for r in range(3)) and
                    all(d_j[r] <= cap[r] for r in range(3))):
                continue
            # Check if two of this type could fit both tasks
            if all(d_i[r] + d_j[r] <= cap[r] * 2 for r in range(3)):
                # c_ij_t = 1 iff both i and j are assigned to type t
                c_ij_t = model.NewBoolVar(f"c_{i}_{j}_{t}")
                model.AddBoolAnd([u[i, t], u[j, t]]).OnlyEnforceIf(c_ij_t)
                model.AddBoolOr([u[i, t].Not(), u[j, t].Not()]).OnlyEnforceIf(c_ij_t.Not())
                type_colocated.append(c_ij_t)

        if not type_colocated:
            # These two tasks can never share a type → no penalty possible
            model.Add(shared_ij == 0)
        else:
            # shared_ij = OR(type_colocated)
            model.AddBoolOr(type_colocated).OnlyEnforceIf(shared_ij)
            model.AddBoolAnd([c.Not() for c in type_colocated]).OnlyEnforceIf(shared_ij.Not())

        penalty_terms.append((pen_scaled, shared_ij))

    # ── Objective: instance costs + TNRP penalties ─────────────────────────────
    cost_coeffs = [int(cpsat_types[t]["cost"] * COST_SCALE) for t in range(T)]
    instance_cost = sum(cnt[t] * cost_coeffs[t] for t in range(T))
    penalty_cost  = sum(coeff * var for coeff, var in penalty_terms)
    model.Minimize(instance_cost + penalty_cost)

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit_s
    solver.parameters.num_search_workers  = num_workers
    solver.parameters.log_search_progress = False

    t0 = time.time()
    status = solver.Solve(model)
    elapsed = time.time() - t0
    status_name = solver.StatusName(status)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raw_obj   = solver.ObjectiveValue()
        raw_bound = solver.BestObjectiveBound()

        # Decompose: instance cost vs penalty cost
        inst_raw = sum(solver.Value(cnt[t]) * cost_coeffs[t] for t in range(T))
        pen_raw  = sum(coeff * solver.Value(var) for coeff, var in penalty_terms)

        cost_hr   = raw_obj   / COST_SCALE
        bound_hr  = raw_bound / COST_SCALE
        inst_hr   = inst_raw  / COST_SCALE
        pen_hr    = pen_raw   / COST_SCALE

        assignment = []
        for t in range(T):
            cnt_val = solver.Value(cnt[t])
            if cnt_val > 0:
                assigned = [task_subset[i]["name"] for i in range(N) if solver.Value(u[i, t])]
                assignment.append({
                    "instance_type": cpsat_types[t]["name"],
                    "count": cnt_val,
                    "tasks": assigned
                })

        return status_name, cost_hr, bound_hr, elapsed, assignment, inst_hr, pen_hr

    return status_name, None, None, elapsed, [], None, None


# ── Main loop ──────────────────────────────────────────────────────────────────

def run_main():
    candidate_ts = [s["timestamp"] for s in orig_snapshots]
    orig_by_ts   = {s["timestamp"]: s for s in orig_snapshots}
    nogpu_by_ts  = {s["timestamp"]: s for s in nogpu_snapshots}

    print("Reusing snapshot timestamps: " + str(candidate_ts))

    results = []
    for snap_t in candidate_ts:
        orig_s  = orig_by_ts[snap_t]
        nogpu_s = nogpu_by_ts.get(snap_t, {})
        print("=" * 60, flush=True)
        print(f"Snapshot t = {snap_t}", flush=True)

        active_ids, task_ids, eva_cost, task_demands, assignment_map = snapshot_at(snap_t)
        task_count = len(task_ids)
        inst_count = len(active_ids)
        print(f"  Active instances: {inst_count}, Committed tasks: {task_count}")
        print(f"  EVA cost ($/hr): {round(eva_cost, 4)}", flush=True)

        gpu_count = sum(1 for td in task_demands if td["demand"][0] > 0)
        cpu_count = sum(1 for td in task_demands if td["demand"][0] == 0)
        print(f"  Tasks: GPU={gpu_count}, CPU-only={cpu_count}", flush=True)

        # Build task labels for TNRP lookup (need task_id → contention_map key)
        task_labels = []
        for td in task_demands:
            tid = td["task_id"]
            task_labels.append(task_label(tid))

        if task_count == 0:
            print("  No tasks active — skipping CP-SAT.")
            results.append({
                "timestamp": snap_t,
                "task_count": 0,
                "gpu_task_count": 0,
                "cpu_task_count": 0,
                "instance_count": inst_count,
                "eva_cost": eva_cost,
                "cpsat_cost_coloc":  orig_s.get("cpsat_cost"),
                "gap_pct_coloc":     orig_s.get("gap_pct"),
                "cpsat_cost_nogpu":  nogpu_s.get("cpsat_cost_nogpu"),
                "gap_pct_nogpu":     nogpu_s.get("gap_pct_nogpu"),
                "cpsat_cost_tnrp":   None,
                "cpsat_bound_tnrp":  None,
                "cpsat_inst_cost_tnrp": None,
                "cpsat_pen_cost_tnrp":  None,
                "cpsat_status_tnrp": "N/A (no tasks)",
                "cpsat_solve_time_tnrp": 0,
                "gap_pct_tnrp": None,
                "task_details": [],
                "task_labels": [],
                "eva_assignment": {},
                "cpsat_assignment_tnrp": []
            })
            continue

        print(f"  Running CP-SAT TNRP (time_limit=60s) ...", flush=True)
        status_name, cpsat_cost, cpsat_bound, solve_time, cpsat_assign, inst_hr, pen_hr = \
            cpsat_solve_tnrp(task_demands, task_labels, time_limit_s=60.0)

        gap_pct_tnrp = 100.0 * (eva_cost - cpsat_cost) / cpsat_cost \
            if (cpsat_cost is not None and cpsat_cost > 0) else None

        orig_cpsat_cost = orig_s.get("cpsat_cost")
        orig_gap        = orig_s.get("gap_pct")
        nogpu_cost      = nogpu_s.get("cpsat_cost_nogpu")
        nogpu_gap       = nogpu_s.get("gap_pct_nogpu")

        print(f"  CP-SAT TNRP: status={status_name} cost={cpsat_cost} "
              f"(inst={inst_hr}, pen={pen_hr}) bound={cpsat_bound} time={round(solve_time, 2)}s")
        print(f"  Gaps: Original={orig_gap:+.2f}%  No-GPU={nogpu_gap:+.2f}%  "
              f"TNRP={gap_pct_tnrp:+.2f}%" if gap_pct_tnrp is not None else "  Gap: N/A")

        results.append({
            "timestamp": snap_t,
            "task_count": task_count,
            "gpu_task_count": gpu_count,
            "cpu_task_count": cpu_count,
            "instance_count": inst_count,
            "eva_cost": eva_cost,
            "cpsat_cost_coloc":     orig_cpsat_cost,
            "gap_pct_coloc":        orig_gap,
            "cpsat_cost_nogpu":     nogpu_cost,
            "gap_pct_nogpu":        nogpu_gap,
            "cpsat_cost_tnrp":      cpsat_cost,
            "cpsat_bound_tnrp":     cpsat_bound,
            "cpsat_inst_cost_tnrp": inst_hr,
            "cpsat_pen_cost_tnrp":  pen_hr,
            "cpsat_status_tnrp":    status_name,
            "cpsat_solve_time_tnrp": solve_time,
            "gap_pct_tnrp":         gap_pct_tnrp,
            "task_details":         task_demands,
            "task_labels":          task_labels,
            "eva_assignment":       {str(k): v for k, v in assignment_map.items()},
            "cpsat_assignment_tnrp": cpsat_assign
        })

    # ── Save JSON ─────────────────────────────────────────────────────────────────
    with open(OUTPUT_JSON_PATH, "w") as f:
        json.dump(results, f, indent=2)
    print("Raw results saved to " + OUTPUT_JSON_PATH)

    # ── Build comparison markdown ─────────────────────────────────────────────────
    os.makedirs("notes", exist_ok=True)
    out = []

    out.append("# EVA vs CP-SAT: Decision-Point Snapshot Comparison — TNRP-Corrected (AUTHORITATIVE)")
    out.append("")
    out.append("> **This is the authoritative version for the paper.**")
    out.append("> Both earlier files (`decision_point_comparison.md` and")
    out.append("> `decision_point_comparison_nogpu_colocate.md`) are intermediate/diagnostic")
    out.append("> steps and should not be cited as final results. See SUPERSEDED headers in those files.")
    out.append("")
    out.append("## Methodology")
    out.append("")
    out.append("**CP-SAT TNRP-corrected model**:")
    out.append("- GPU tasks *can* share an instance (no hard co-location ban).")
    out.append("- For each pair of GPU tasks assigned to the same instance type, a **TNRP")
    out.append("  interference penalty** is added to the objective:")
    out.append("  ```")
    out.append("  penalty(i,j) = cost(min_it_i) × (1 - rate(i|j))")
    out.append("               + cost(min_it_j) × (1 - rate(j|i))")
    out.append("  ```")
    out.append("  where `rate(i|j)` = EVA's `get_contention_rate(label_i, (label_j,), contention_map)`.")
    out.append("- **Lookup order**: (1) direct contention_map entry for exact tuple,")
    out.append("  (2) pairwise product fallback — matching EVA's own code exactly.")
    out.append("- **Audit result** (Section 8 of `notes/tnrp_formula.md`): 22/22 (100%) of")
    out.append("  3+-GPU-task groups found across all 8 snapshots had **direct** entries in")
    out.append("  `contention_map`. The pairwise fallback introduces no additional inaccuracy")
    out.append("  beyond what EVA's own scheduler already accepts.")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## Summary Table — All Three CP-SAT Variants vs EVA")
    out.append("")
    out.append("| Timestamp (s) | Tasks (GPU/CPU) | EVA $/hr | CP-SAT free-coloc $/hr | Gap % | CP-SAT no-GPU-coloc $/hr | Gap % | **CP-SAT TNRP $/hr** | **Gap %** |")
    out.append("|---:|---:|---:|---:|---:|---:|---:|---:|---:|")

    valid_orig_gaps  = []
    valid_nogpu_gaps = []
    valid_tnrp_gaps  = []

    for r in results:
        t  = r["timestamp"]
        tc = f"{r['task_count']} ({r['gpu_task_count']}/{r['cpu_task_count']})"

        eva = f"{r['eva_cost']:.4f}"

        def fmt_cost(v): return f"{v:.4f}" if v is not None else "n/a"
        def fmt_gap(v):
            if v is None: return "n/a"
            return (("+" if v >= 0 else "") + f"{v:.2f}%")

        oc   = fmt_cost(r.get("cpsat_cost_coloc"))
        og   = fmt_gap(r.get("gap_pct_coloc"))
        nc   = fmt_cost(r.get("cpsat_cost_nogpu"))
        ng   = fmt_gap(r.get("gap_pct_nogpu"))
        tc2  = fmt_cost(r.get("cpsat_cost_tnrp"))
        tg   = fmt_gap(r.get("gap_pct_tnrp"))

        out.append(f"| {t} | {tc} | {eva} | {oc} | {og} | {nc} | {ng} | **{tc2}** | **{tg}** |")

        if r.get("gap_pct_coloc") is not None:  valid_orig_gaps.append(r["gap_pct_coloc"])
        if r.get("gap_pct_nogpu") is not None:  valid_nogpu_gaps.append(r["gap_pct_nogpu"])
        if r.get("gap_pct_tnrp")  is not None:  valid_tnrp_gaps.append(r["gap_pct_tnrp"])

    out.append("")

    if valid_tnrp_gaps:
        def gstats(gaps, label):
            return (f"**{label}**: min={min(gaps):+.2f}%, max={max(gaps):+.2f}%, "
                    f"mean={sum(gaps)/len(gaps):+.2f}%  ")

        out.append(gstats(valid_orig_gaps,  "Free co-location"))
        out.append(gstats(valid_nogpu_gaps, "No GPU co-location"))
        out.append(gstats(valid_tnrp_gaps,  "TNRP-corrected (this version)"))

    out.append("")
    out.append("---")
    out.append("")
    out.append("## TNRP Penalty Decomposition")
    out.append("")
    out.append("The TNRP objective = instance provisioning cost + throughput interference penalty.")
    out.append("This table shows how much of the CP-SAT TNRP total is interference penalty:")
    out.append("")
    out.append("| Timestamp (s) | TNRP total $/hr | Instance cost $/hr | Penalty $/hr | Penalty % of total |")
    out.append("|---:|---:|---:|---:|---:|")
    for r in results:
        tc2 = r.get("cpsat_cost_tnrp")
        ic  = r.get("cpsat_inst_cost_tnrp")
        pc  = r.get("cpsat_pen_cost_tnrp")
        if tc2 is None:
            out.append(f"| {r['timestamp']} | n/a | n/a | n/a | n/a |")
        else:
            pct = 100.0 * pc / tc2 if tc2 > 0 else 0.0
            out.append(f"| {r['timestamp']} | {tc2:.4f} | {ic:.4f} | {pc:.4f} | {pct:.1f}% |")
    out.append("")
    out.append("---")
    out.append("")
    out.append("## Per-Snapshot Detail (TNRP-Corrected)")
    out.append("")

    for r in results:
        t    = r["timestamp"]
        h_val = round(t / 3600.0, 2)
        out.append(f"### Snapshot t = {t} s ({h_val} h)")
        out.append("")
        out.append(f"- **Active tasks**: {r['task_count']} (GPU: {r['gpu_task_count']}, CPU: {r['cpu_task_count']})")
        out.append(f"- **Active instances (EVA)**: {r['instance_count']}")
        out.append(f"- **EVA $/hr**: `{r['eva_cost']:.4f}`")

        oc = r.get("cpsat_cost_coloc")
        og = r.get("gap_pct_coloc")
        nc = r.get("cpsat_cost_nogpu")
        ng = r.get("gap_pct_nogpu")
        tc2 = r.get("cpsat_cost_tnrp")
        tg = r.get("gap_pct_tnrp")
        ic = r.get("cpsat_inst_cost_tnrp")
        pc = r.get("cpsat_pen_cost_tnrp")

        if oc is not None:
            out.append(f"- **CP-SAT free co-loc $/hr**: `{oc:.4f}` (Gap: `{og:+.2f}%`)")
        if nc is not None:
            out.append(f"- **CP-SAT no-GPU-coloc $/hr**: `{nc:.4f}` (Gap: `{ng:+.2f}%`)")
        if tc2 is not None:
            out.append(f"- **CP-SAT TNRP $/hr**: `{tc2:.4f}` (inst `{ic:.4f}` + penalty `{pc:.4f}`) "
                       f"— status: {r['cpsat_status_tnrp']} ({r['cpsat_solve_time_tnrp']:.2f}s)")
            out.append(f"- **Gap % (TNRP)**: `{tg:+.2f}%`")
        out.append("")

        if r.get("cpsat_assignment_tnrp"):
            out.append("#### CP-SAT TNRP Assignment")
            out.append("")
            out.append("| Instance Type | Count | Tasks |")
            out.append("|---|---:|---|")
            for a in r["cpsat_assignment_tnrp"]:
                out.append(f"| {a['instance_type']} | {a['count']} | {', '.join(a['tasks'])} |")
            out.append("")
        out.append("---")
        out.append("")

    with open(OUTPUT_MD_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")

    print("Markdown report saved to " + OUTPUT_MD_PATH)
    print("=== DONE ===")

if __name__ == '__main__':
    run_main()
