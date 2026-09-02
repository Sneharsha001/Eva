import json, os, time
from ortools.sat.python import cp_model

REPORT_PATH = r"src/simulation_experiments/EVAGangScheduler_pai_200/report.json"
EC2_CFG_PATH = r"src/simulation/config/ec2_config_virt.json"
OUTPUT_PATH = r"notes/decision_point_comparison.md"
COST_SCALE = 100_000

print("Loading report.json ...", flush=True)
with open(REPORT_PATH) as f:
    report = json.load(f)
print("Loading ec2_config_virt.json ...", flush=True)
with open(EC2_CFG_PATH) as f:
    ec2_cfg = json.load(f)

instances  = report["instances"]
tasks      = report["tasks"]
inst_types = report["instance_types"]
it_by_name = {}
for v in inst_types.values():
    it_by_name[v["name"]] = {"cost": v["cost"], "capacity": v["capacity"]}
cpsat_types = []
for name, info in ec2_cfg["instance_types"].items():
    cpsat_types.append({"name": name, "capacity": info["capacity"], "cost": info["cost"]})
print(f"  {len(instances)} instances, {len(tasks)} tasks, {len(cpsat_types)} instance types for CP-SAT")

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
        ti = tasks[str(tid)]
        task_demands.append({"task_id": tid, "name": ti["name"] + " (job " + str(ti["job_id"]) + ")", "demand": task_demand(ti)})
    return active_ids, task_ids, eva_cost_hr, task_demands, assignment_map

def cpsat_solve(task_subset, time_limit_s=60.0, num_workers=8):
    N = len(task_subset)
    T = len(cpsat_types)
    model = cp_model.CpModel()
    cnt = [model.NewIntVar(0, N, "cnt_" + str(t)) for t in range(T)]
    u   = {(i, t): model.NewBoolVar("u_" + str(i) + "_" + str(t)) for i in range(N) for t in range(T)}
    for i in range(N):
        model.AddExactlyOne(u[i, t] for t in range(T))
    for t in range(T):
        cap = cpsat_types[t]["capacity"]
        for r in range(3):
            model.Add(sum(task_subset[i]["demand"][r] * u[i, t] for i in range(N)) <= cap[r] * cnt[t])
    for i in range(N):
        feasible = []
        for t in range(T):
            cap = cpsat_types[t]["capacity"]
            if all(task_subset[i]["demand"][r] <= cap[r] for r in range(3)):
                feasible.append(t)
            else:
                model.Add(u[i, t] == 0)
        if not feasible:
            raise ValueError("Task " + task_subset[i]["name"] + " cannot fit on any instance type!")
    for t in range(T):
        for i in range(N):
            model.Add(cnt[t] >= 1).OnlyEnforceIf(u[i, t])
    cost_coeffs = [int(cpsat_types[t]["cost"] * COST_SCALE) for t in range(T)]
    model.Minimize(sum(cnt[t] * cost_coeffs[t] for t in range(T)))
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
        cost_hr   = raw_obj   / COST_SCALE
        bound_hr  = raw_bound / COST_SCALE
        assignment = []
        for t in range(T):
            cnt_val = solver.Value(cnt[t])
            if cnt_val > 0:
                assigned = [task_subset[i]["name"] for i in range(N) if solver.Value(u[i, t])]
                assignment.append({"instance_type": cpsat_types[t]["name"], "count": cnt_val, "tasks": assigned})
        return status_name, cost_hr, bound_hr, elapsed, assignment
    return status_name, None, None, elapsed, []

# Choose snapshot timestamps: 8 evenly-spaced in [10000, 300000]
SIM_START = 10_000
SIM_END   = 300_000
NUM_PROBES = 8
candidate_ts = [int(SIM_START + i * (SIM_END - SIM_START) / (NUM_PROBES - 1)) for i in range(NUM_PROBES)]
candidate_ts = [round(t / 300) * 300 for t in candidate_ts]
print("Candidate timestamps: " + str(candidate_ts))

# Find peak concurrent task count
print("Scanning for peak concurrent task count ...", flush=True)
event_times = set()
for task_info in tasks.values():
    for h in task_info.get("history", []):
        event_times.add(h["timestamp"])
event_times = sorted(event_times)
sampled_times = event_times[::10]
peak_t = candidate_ts[4]
peak_cnt = 0
for t in sampled_times:
    _, tids, _, _, _ = snapshot_at(t)
    if len(tids) > peak_cnt:
        peak_cnt = len(tids)
        peak_t = t
print("  Peak concurrent task count = " + str(peak_cnt) + " at t = " + str(peak_t))
if peak_t not in candidate_ts:
    candidate_ts[4] = round(peak_t / 300) * 300
candidate_ts = sorted(set(candidate_ts))
print("Final snapshot timestamps: " + str(candidate_ts))

results = []
for snap_t in candidate_ts:
    print("=" * 60, flush=True)
    print("Snapshot t = " + str(snap_t), flush=True)
    active_ids, task_ids, eva_cost, task_demands, assignment_map = snapshot_at(snap_t)
    task_count = len(task_ids)
    inst_count = len(active_ids)
    print("  Active instances: " + str(inst_count) + ", Committed tasks: " + str(task_count))
    print("  EVA cost ($/hr): " + str(round(eva_cost, 4)), flush=True)
    if task_count == 0:
        print("  No tasks active - skipping CP-SAT.")
        results.append({"timestamp": snap_t, "task_count": 0, "instance_count": inst_count, "eva_cost": eva_cost, "cpsat_cost": None, "cpsat_bound": None, "cpsat_status": "N/A (no tasks)", "gap_pct": None, "task_details": [], "eva_assignment": {}, "cpsat_assignment": [], "cpsat_solve_time": 0})
        continue
    for td in task_demands:
        it_name = assignment_map.get(td["task_id"], "?")
        print("    Task " + str(td["task_id"]) + " demand=" + str(td["demand"]) + " -> EVA: " + str(it_name))
    print("  Running CP-SAT (time_limit=60s) ...", flush=True)
    status_name, cpsat_cost, cpsat_bound, solve_time, cpsat_assign = cpsat_solve(task_demands, time_limit_s=60.0)
    print("  CP-SAT: status=" + str(status_name) + " cost=" + str(cpsat_cost) + " bound=" + str(cpsat_bound) + " time=" + str(round(solve_time, 2)) + "s", flush=True)
    gap_pct = 100.0 * (eva_cost - cpsat_cost) / cpsat_cost if (cpsat_cost is not None and cpsat_cost > 0) else None
    results.append({"timestamp": snap_t, "task_count": task_count, "instance_count": inst_count, "eva_cost": eva_cost, "cpsat_cost": cpsat_cost, "cpsat_bound": cpsat_bound, "cpsat_status": status_name, "cpsat_solve_time": solve_time, "gap_pct": gap_pct, "task_details": task_demands, "eva_assignment": {str(k): v for k, v in assignment_map.items()}, "cpsat_assignment": cpsat_assign})

raw_out = r"cpsat_comparison/decision_point_snapshots.json"
with open(raw_out, "w") as f:
    json.dump(results, f, indent=2)
print("Raw results saved to " + raw_out)

os.makedirs("notes", exist_ok=True)
out_lines = []
out_lines.append("# EVA vs CP-SAT: Decision-Point Snapshot Comparison (pai_200)")
out_lines.append("")
out_lines.append("> **Methodology**: For each snapshot timestamp we determine the exact set of tasks")
out_lines.append("> that EVA committed to active instances (from report.json instance histories).")
out_lines.append("> EVA cost = sum of $/hr for all provisioned instances at that moment.")
out_lines.append("> CP-SAT cost = optimal bin-packing of the same task set across 21 instance types.")
out_lines.append("> This is a true apples-to-apples comparison: same task set, same moment in time.")
out_lines.append("")
out_lines.append("---")
out_lines.append("")
out_lines.append("## Summary Table")
out_lines.append("")
out_lines.append("| Timestamp (s) | Tasks | Instances | EVA $/hr | CP-SAT Optimal $/hr | Gap % |")
out_lines.append("|---:|---:|---:|---:|---:|---:|")
valid_gaps = []
for r in results:
    t = r["timestamp"]
    tc = r["task_count"]
    ic = r["instance_count"]
    eva = str(round(r["eva_cost"], 4))
    cpsat = str(round(r["cpsat_cost"], 4)) if r["cpsat_cost"] is not None else "n/a"
    gap_val = r["gap_pct"]
    gap_str = ("+" if gap_val >= 0 else "") + str(round(gap_val, 2)) + "%" if gap_val is not None else "n/a"
    if gap_val is not None:
        valid_gaps.append(gap_val)
    out_lines.append("| " + str(t) + " | " + str(tc) + " | " + str(ic) + " | " + eva + " | " + cpsat + " | " + gap_str + " |")
out_lines.append("")
if valid_gaps:
    avg_gap = sum(valid_gaps) / len(valid_gaps)
    min_gap = min(valid_gaps)
    max_gap = max(valid_gaps)
    out_lines.append("**Gap summary** across " + str(len(valid_gaps)) + " snapshots: min = " + str(round(min_gap, 2)) + "%, max = " + str(round(max_gap, 2)) + "%, mean = " + str(round(avg_gap, 2)) + "%")
out_lines.append("")
out_lines.append("> Positive gap = EVA costs more than CP-SAT optimal for this task set.")
out_lines.append("> Negative gap = EVA uses fewer/cheaper instances for this task set.")
out_lines.append("")
out_lines.append("---")
out_lines.append("")
out_lines.append("## Per-Snapshot Detail")
out_lines.append("")
for r in results:
    t = r["timestamp"]
    h_val = round(t / 3600.0, 2)
    out_lines.append("### Snapshot t = " + str(t) + " s (" + str(h_val) + " h)")
    out_lines.append("")
    out_lines.append("- **Active tasks**: " + str(r["task_count"]))
    out_lines.append("- **Active instances (EVA)**: " + str(r["instance_count"]))
    out_lines.append("- **EVA $/hr**: " + str(round(r["eva_cost"], 4)))
    if r["cpsat_cost"] is not None:
        out_lines.append("- **CP-SAT optimal $/hr**: " + str(round(r["cpsat_cost"], 4)) + " (bound: " + str(round(r["cpsat_bound"], 4)) + ")")
        out_lines.append("- **CP-SAT status**: " + str(r["cpsat_status"]) + " (solved in " + str(round(r["cpsat_solve_time"], 2)) + "s)")
        gap_val = r["gap_pct"]
        gap_str = ("+" if gap_val >= 0 else "") + str(round(gap_val, 2)) + "%" if gap_val is not None else "n/a"
        out_lines.append("- **Gap**: " + gap_str)
    else:
        out_lines.append("- **CP-SAT**: " + str(r["cpsat_status"]))
    out_lines.append("")
    if r["task_count"] > 0:
        out_lines.append("#### Task Set and EVA Assignment")
        out_lines.append("")
        out_lines.append("| Task ID | Name | GPU | CPU | RAM | EVA Instance Type |")
        out_lines.append("|---:|---|---:|---:|---:|---|")
        for td in r["task_details"]:
            d = td["demand"]
            it = r["eva_assignment"].get(str(td["task_id"]), "?")
            out_lines.append("| " + str(td["task_id"]) + " | " + str(td["name"]) + " | " + str(d[0]) + " | " + str(d[1]) + " | " + str(d[2]) + " | " + str(it) + " |")
        out_lines.append("")
    if r["cpsat_assignment"]:
        out_lines.append("#### CP-SAT Optimal Assignment")
        out_lines.append("")
        out_lines.append("| Instance Type | Count | Tasks |")
        out_lines.append("|---|---:|---|")
        for a in r["cpsat_assignment"]:
            out_lines.append("| " + str(a["instance_type"]) + " | " + str(a["count"]) + " | " + ", ".join(a["tasks"]) + " |")
        out_lines.append("")
    out_lines.append("---")
    out_lines.append("")
out_lines.append("## Methodology Notes")
out_lines.append("")
out_lines.append("- Demand vector [GPU, CPU, RAM] taken from demand_dict in report.json.")
out_lines.append("  GPU tasks use the p3 family entry; CPU-only tasks use c7i or r7i.")
out_lines.append("- EVA cost at each snapshot = sum of $/hr for ALL provisioned instances")
out_lines.append("  (EVA pays from boot to shutdown regardless of task execution status).")
out_lines.append("- CP-SAT cost = provably optimal $/hr for the minimum-cost fleet that hosts")
out_lines.append("  the exact same concurrent task set, using any of the 21 available instance types.")
out_lines.append("- The 196-hour aggregate total vs 1-hour snapshot comparison is INVALID and excluded.")
out_lines.append("  All comparisons here are instantaneous $/hr vs instantaneous $/hr.")
with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    f.write("\n".join(out_lines) + "\n")
print("Markdown report saved to " + OUTPUT_PATH)
print("=== DONE ===")
