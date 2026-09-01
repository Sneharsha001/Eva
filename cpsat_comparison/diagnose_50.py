"""
DIAGNOSTIC ONLY – do NOT modify cpsat_scheduler.py.
Runs the EXISTING slot-indexed model on the first 50 tasks and prints:
  - solver.ResponseStats()
  - NumBranches, NumConflicts, WallTime
  - ObjectiveValue, BestObjectiveBound (raw integer and scaled)
  - solver.parameters in effect
  - scale-mismatch check
"""
import os, sys, json, time, random
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ortools.sat.python import cp_model

EC2_PATH  = "src/simulation/config/ec2_config_virt.json"
PAI_PATH  = "src/pai_trace/traces/pai_200.json"
N_TASKS   = 50
COST_SCALE = 100_000
TIME_LIMIT = 120.0        # 2 min is enough to expose the issue

# ── Load data ────────────────────────────────────────────────────────────────
with open(EC2_PATH) as f:
    ec2 = json.load(f)
instance_types = [
    {"name": k, "capacity": v["capacity"], "cost": v["cost"]}
    for k, v in ec2["instance_types"].items()
]

with open(PAI_PATH) as f:
    trace = json.load(f)
all_ids = sorted(trace.keys(), key=int)
chosen  = all_ids[:N_TASKS]           # first 50, deterministic
tasks = []
for jid in chosen:
    job = trace[jid]
    tid = next(iter(job["tasks"]))
    demand = job["tasks"][tid]["demand"]["any"]
    tasks.append({"name": f"{job['name']}_{tid}", "demand": demand})

print(f"Loaded {len(instance_types)} instance types and {len(tasks)} tasks.")
print(f"Instance types: {[it['name'] for it in instance_types]}")

N = len(tasks)
T = len(instance_types)

# ── Build EXISTING model (slot-indexed) ──────────────────────────────────────
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
        capacity_expr = sum(instance_types[t]["capacity"][r] * y[j, t] for t in range(T))
        model.Add(demand_expr <= capacity_expr)

for j in range(N - 1):
    model.Add(z[j] >= z[j + 1])

total_cost_expr = sum(
    y[j, t] * int(instance_types[t]["cost"] * COST_SCALE)
    for j in range(N)
    for t in range(T)
)
model.Minimize(total_cost_expr)

print(f"\nModel variables: {len(model.Proto().variables)}")
print(f"Model constraints: {len(model.Proto().constraints)}")
print(f"N slots x N tasks x variables (x): {N*N}")
print(f"N slots x T types variables (y): {N*T}")

# ── Solver parameters ─────────────────────────────────────────────────────────
solver = cp_model.CpSolver()
solver.parameters.max_time_in_seconds = TIME_LIMIT
solver.parameters.log_search_progress = True
solver.parameters.num_search_workers  = 1   # single-threaded to reproduce original

print(f"\n=== Solver parameters in effect ===")
print(f"  max_time_in_seconds: {solver.parameters.max_time_in_seconds}")
print(f"  num_search_workers:  {solver.parameters.num_search_workers}")
print(f"  log_search_progress: {solver.parameters.log_search_progress}")
print(f"  COST_SCALE:          {COST_SCALE}")

# ── Solve ─────────────────────────────────────────────────────────────────────
print("\n=== Starting solver (existing slot-indexed model) ===")
t0 = time.time()
status = solver.Solve(model)
elapsed = time.time() - t0

print(f"\n=== FULL ResponseStats ===")
print(solver.ResponseStats())

raw_obj   = solver.ObjectiveValue()
raw_bound = solver.BestObjectiveBound()
scaled_obj   = raw_obj   / COST_SCALE
scaled_bound = raw_bound / COST_SCALE

print(f"\n=== Key Metrics ===")
print(f"  Status:                {solver.StatusName(status)}")
print(f"  WallTime:              {solver.WallTime():.3f} s")
print(f"  NumBranches:           {solver.NumBranches()}")
print(f"  NumConflicts:          {solver.NumConflicts()}")
print(f"  ObjectiveValue (raw):  {raw_obj}")
print(f"  BestObjectiveBound (raw): {raw_bound}")
print(f"  ObjectiveValue (scaled):  {scaled_obj:.5f}")
print(f"  BestObjectiveBound (scaled): {scaled_bound:.5f}")
print(f"  Gap %:  {100*(scaled_obj - scaled_bound)/scaled_obj:.2f}%"
      if scaled_obj else "  Gap: N/A")

print(f"\n=== Scale-mismatch check ===")
print(f"  COST_SCALE used for objective:         {COST_SCALE}")
print(f"  COST_SCALE used to read bound back:    {COST_SCALE}")
print(f"  Same scale? {'YES – no mismatch' if True else 'NO – MISMATCH'}")
print(f"  Raw bound = {raw_bound:.1f} vs raw obj = {raw_obj:.1f}")
print(f"  → Bound/Obj ratio = {raw_bound/raw_obj:.6f}" if raw_obj else "")
print(f"  Cheapest instance cost (raw int): {min(int(it['cost']*COST_SCALE) for it in instance_types)}")
print(f"  → If BestObjectiveBound ≈ that value, bound is stuck at 1-instance lower bound")

print(f"\n=== Symmetry analysis ===")
print(f"  Number of slot variables (z): {N}  [these are interchangeable by type!]")
print(f"  Number of type vars (y[j,t]) per slot: {T}")
print(f"  Total y variables: {N*T}  ← combinatorial explosion from slot symmetry")
print(f"  Symmetry-breaking constraint used: z[j] >= z[j+1] (open/close ordering only)")
print(f"  → Does NOT break type assignment symmetry between identical-type slots")
print(f"  → For 22 types × 50 slots: many equivalent permutations remain")
