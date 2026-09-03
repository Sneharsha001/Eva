"""
audit_3way_contention.py
========================
For each of the 8 decision-point snapshots, examine every group of 3+ co-located
tasks that EVA actually formed, and determine whether EVA's contention_map has a
DIRECT entry for the exact co-location tuple, or whether it would fall back to the
pairwise product approximation.

Outputs a detailed table for notes/tnrp_formula.md.
"""
import json, ast

REPORT_PATH    = r"src/simulation_experiments/EVAGangScheduler_pai_200/report.json"
SNAPSHOTS_PATH = r"cpsat_comparison/decision_point_snapshots.json"

print("Loading report.json ...", flush=True)
with open(REPORT_PATH) as f:
    report = json.load(f)

print("Loading decision_point_snapshots.json ...", flush=True)
with open(SNAPSHOTS_PATH) as f:
    snapshots = json.load(f)

instances  = report["instances"]
tasks_data = report["tasks"]
cm         = report["contention_map"]

# ── Helpers ────────────────────────────────────────────────────────────────────

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
    return list(committed)

def task_label(tid):
    """Return 'job_name_task_name' string for this task, matching contention_map key format."""
    t = tasks_data[str(tid)]
    job_id = t["job_id"]
    job_name = report["jobs"][str(job_id)]["name"]
    task_name = t["name"]
    return f"{job_name}_{task_name}"

def has_gpu(tid):
    t = tasks_data[str(tid)]
    for fam, demand in t["demand_dict"].items():
        if demand[0] > 0:
            return True
    return False

def lookup_rate(key, value_tuple, contention_map):
    """Mirrors EVA's get_contention_rate exactly."""
    DEFAULT = 0.95
    if key not in contention_map:
        return ("key_miss_fallback", pow(DEFAULT, len(value_tuple)))

    cm_key = contention_map[key]
    # contention_map keys are stored as string representations of tuples in the JSON
    # We need to match value_tuple against the string keys
    value_str = str(value_tuple)
    if value_str in cm_key:
        vals = cm_key[value_str]
        return ("direct", sum(vals) / len(vals))

    # Also try matching with tuple converted to canonical form
    # The JSON may have keys like "('a', 'b')" stored as string
    for k_str, vals in cm_key.items():
        try:
            k_tup = ast.literal_eval(k_str)
            if tuple(sorted(k_tup)) == tuple(sorted(value_tuple)):
                return ("direct", sum(vals) / len(vals))
        except Exception:
            pass

    if len(value_tuple) == 1:
        return ("singleton_fallback", DEFAULT)

    # pairwise product fallback
    product = 1.0
    for v in value_tuple:
        r = lookup_rate(key, (v,), contention_map)
        product *= r[1]
    return ("pairwise_product_fallback", product)


# ── Audit each snapshot ────────────────────────────────────────────────────────

print(f"\nProcessing {len(snapshots)} snapshots...\n")

total_groups_3plus  = 0   # total 3+-way groups found across all snapshots
direct_hits         = 0   # groups with a direct contention_map entry
fallback_groups     = []  # (snapshot_ts, instance_id, group_labels, reason)
direct_group_detail = []  # (snapshot_ts, instance_id, group_labels, rate)

for snap in snapshots:
    ts = snap["timestamp"]
    snap_task_ids_in_snapshot = {td["task_id"] for td in snap["task_details"]}

    # Find all active instances at this timestamp and their committed task groups
    instance_groups = {}  # inst_id -> [task_id, ...]
    for inst_id_str, inst in instances.items():
        if not instance_active_at(inst, ts):
            continue
        ctasks = committed_tasks_at(inst, ts)
        # Only keep tasks that exist in our tasks_data
        ctasks = [t for t in ctasks if str(t) in tasks_data]
        if len(ctasks) < 3:
            continue
        # Check if at least 2 are GPU tasks (demand[0] > 0)
        gpu_tasks = [t for t in ctasks if has_gpu(t)]
        if len(gpu_tasks) < 3:
            continue
        instance_groups[inst_id_str] = ctasks

    for inst_id_str, group in instance_groups.items():
        gpu_tasks = [t for t in group if has_gpu(t)]
        if len(gpu_tasks) < 3:
            continue

        total_groups_3plus += 1
        group_labels = tuple(sorted(task_label(t) for t in gpu_tasks))
        print(f"  ts={ts} inst={inst_id_str}: {len(gpu_tasks)}-GPU group: {group_labels}")

        # For each task in the group, check if its contention lookup would be direct or fallback
        group_results = []
        for tid in gpu_tasks:
            key = task_label(tid)
            others = tuple(sorted(task_label(t) for t in gpu_tasks if t != tid))
            status, rate = lookup_rate(key, others, cm)
            group_results.append((key, others, status, rate))
            print(f"    task={key!r}  others={others}  -> {status}  rate={rate:.4f}")

        # A group "has direct" if ALL per-task lookups are direct
        group_all_direct = all(r[2] == "direct" for r in group_results)
        any_fallback = any("fallback" in r[2] for r in group_results)

        if group_all_direct:
            direct_hits += 1
            direct_group_detail.append((ts, inst_id_str, group_labels))
            print(f"    => ALL DIRECT")
        else:
            fallback_groups.append((ts, inst_id_str, group_labels,
                                    [r[2] for r in group_results]))
            print(f"    => PARTIAL/FULL FALLBACK: {[r[2] for r in group_results]}")

# ── Summary ───────────────────────────────────────────────────────────────────

print("\n" + "="*60)
print(f"Total 3+-GPU-task co-located groups found: {total_groups_3plus}")
print(f"  All-direct lookup:      {direct_hits}  ({direct_hits/total_groups_3plus*100:.1f}% if total>0)")
print(f"  At least one fallback:  {len(fallback_groups)}  ({len(fallback_groups)/total_groups_3plus*100:.1f}% if total>0)")

if total_groups_3plus == 0:
    print("\nNOTE: No 3+-GPU-task groups found in any of the 8 snapshots.")
    print("This means Option A (pairwise approximation) introduces ZERO inaccuracy")
    print("beyond what EVA itself accepts — there is nothing to approximate.")
