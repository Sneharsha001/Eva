"""
Generate notes/comparison_report.md and notes/scalability.png.
Reads:
  - notes/eva_baseline_results.json      (written from confirmed log output)
  - cpsat_comparison/cpsat_results.json  (written by cpsat_scheduler.py)
  - cpsat_comparison/scalability_results.json (written by scalability_sweep.py)
No imports from src/.
"""
import os
import json
import sys

# Locate matplotlib from venv if needed
try:
    import matplotlib
except ImportError:
    venv_sp = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "venv", "Lib", "site-packages"
    )
    sys.path.insert(0, venv_sp)
    import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

NOTES_DIR     = "notes"
CPSAT_RESULTS = "cpsat_comparison/cpsat_results.json"
SCALE_RESULTS = "cpsat_comparison/scalability_results.json"
BASELINE      = "notes/eva_baseline_results.json"
REPORT_MD     = os.path.join(NOTES_DIR, "comparison_report.md")
PLOT_PNG      = os.path.join(NOTES_DIR, "scalability.png")

os.makedirs(NOTES_DIR, exist_ok=True)

# ─── 1. Load simulation baseline ─────────────────────────────────────────────
with open(BASELINE) as f:
    sim_data = json.load(f)

naive_cost = next(
    r["total cost"] for r in sim_data if r["scheduler name"] == "NaiveScheduler"
)

def pct_vs_naive(cost):
    if cost is None:
        return "—"
    return f"{(cost / naive_cost) * 100:.1f}%"

# ─── 2. Load CP-SAT 200-task result ──────────────────────────────────────────
cpsat_200 = None
if os.path.exists(CPSAT_RESULTS):
    with open(CPSAT_RESULTS) as f:
        data = json.load(f)
    cpsat_200 = data[0] if data else None

# ─── 3. Load scalability sweep ───────────────────────────────────────────────
scale_rows = []
if os.path.exists(SCALE_RESULTS):
    with open(SCALE_RESULTS) as f:
        scale_rows = json.load(f)

# ─── 4. Build table rows ─────────────────────────────────────────────────────
table_rows = []
for r in sim_data:
    table_rows.append({
        "name":  r["scheduler name"],
        "cost":  r["total cost"],
        "time":  f"{r['runtime']}s (sim)",
        "pct":   pct_vs_naive(r["total cost"]),
        "note":  "",
    })

if cpsat_200:
    cpsat_cost   = cpsat_200.get("total cost")
    cpsat_status = cpsat_200.get("solve_status", "?")
    cpsat_time   = cpsat_200.get("runtime")
    cpsat_bound  = cpsat_200.get("best bound")
    time_str = f"{cpsat_time:.1f}s" if cpsat_time is not None else "—"
    note_str = cpsat_status
    if cpsat_bound is not None and cpsat_status != "OPTIMAL":
        note_str += f"; best_bound=${cpsat_bound:,.2f}"
    table_rows.append({
        "name": "CP-SAT (ILP)",
        "cost": cpsat_cost,
        "time": time_str,
        "pct":  pct_vs_naive(cpsat_cost),
        "note": note_str,
    })
else:
    table_rows.append({
        "name": "CP-SAT (ILP)",
        "cost": None,
        "time": "—",
        "pct":  "—",
        "note": "result pending",
    })

# ─── 5. Write Markdown ───────────────────────────────────────────────────────
lines = []
lines.append("# EVA Scheduler vs CP-SAT ILP: Comparison Report\n")
lines.append(
    "_All scheduler costs are total cloud spend ($) over the full simulation horizon._  \n"
    "_CP-SAT models the static bin-packing ILP from EVA paper §4.1: minimize hourly cost_  \n"
    "_of instances needed to pack all 200 tasks simultaneously._\n"
)

lines.append("\n## Section 1 — Cost Comparison Table (200-task `pai_200` trace)\n")
lines.append(
    "| Scheduler / Method | Total Cost ($) | Solve / Run Time | % of No-Packing | Notes |"
)
lines.append("|---|---:|---:|---:|---|")
for r in table_rows:
    cost_str = f"{r['cost']:,.2f}" if r["cost"] is not None else "—"
    lines.append(
        f"| {r['name']} | {cost_str} | {r['time']} | {r['pct']} | {r['note']} |"
    )

lines.append("\n> **No-Packing baseline** = `NaiveScheduler` ($35,858.35).  \n")
lines.append(
    "> EVA (`EVAGangScheduler`) achieves the lowest cost among dynamic schedulers "
    "($25,190.69, 70.2% of No-Packing).\n"
)

# CP-SAT vs best sim
if cpsat_200 and cpsat_200.get("total cost"):
    cpsat_c = cpsat_200["total cost"]
    best_sim = min(r["total cost"] for r in sim_data)
    best_sched = next(r["scheduler name"] for r in sim_data if r["total cost"] == best_sim)
    if cpsat_c < best_sim:
        lines.append(
            f"> **CP-SAT beats all schedulers**: ${cpsat_c:,.2f} < ${best_sim:,.2f} ({best_sched}).\n"
        )
    else:
        lines.append(
            f"> CP-SAT (${cpsat_c:,.2f}) does **not** beat the best scheduler "
            f"({best_sched} at ${best_sim:,.2f}) — note CP-SAT is a static snapshot cost,  \n"
            "> whereas simulator costs accumulate over time with dynamic provisioning.\n"
        )

# ─── 6. Scalability section ──────────────────────────────────────────────────
lines.append("\n## Section 2 — CP-SAT Scalability Sweep\n")
lines.append(
    "Tasks sampled from `pai_full.json` (6,274 jobs) with `random.seed(42)`.  \n"
    "Time limit: **30 minutes** per solve.  \n"
    "Scale costs = $/hr of instances needed to place all N tasks simultaneously.\n"
)

if scale_rows:
    lines.append(
        "\n| N Tasks | Status | Total Cost ($) | Best Bound ($) | Solve Time (s) |"
    )
    lines.append("|---:|---|---:|---:|---:|")
    for r in scale_rows:
        cost_str  = f"{r['cost']:,.2f}"        if r.get("cost")       is not None else "—"
        bound_str = f"{r['best_bound']:,.2f}"  if r.get("best_bound") is not None else "—"
        time_str  = f"{r['solve_time']:.1f}"   if r.get("solve_time") is not None else "—"
        lines.append(
            f"| {r['n_tasks']} | {r['status']} | {cost_str} | {bound_str} | {time_str} |"
        )

    optimal_sizes = [r["n_tasks"] for r in scale_rows if r["status"] == "OPTIMAL"]
    non_optimal   = [r["n_tasks"] for r in scale_rows
                     if r["status"] not in ("OPTIMAL", "FEASIBLE", "SKIPPED", None)
                     and r.get("n_tasks")]

    if non_optimal:
        first_fail = min(non_optimal)
        lines.append(
            f"\n> **CP-SAT first fails to reach OPTIMAL within 30 minutes at N = {first_fail} tasks.**\n"
        )
    elif optimal_sizes:
        lines.append(
            f"\n> CP-SAT reached OPTIMAL for all tested sizes up to N = {max(optimal_sizes)}.\n"
        )
else:
    lines.append("\n_Scalability sweep results not yet available._\n")

# ─── 7. Plot reference ───────────────────────────────────────────────────────
lines.append("\n## Section 3 — Scalability Plot\n")
lines.append(
    "![Solve time vs task count](scalability.png)\n\n"
    "_Dashed red line = 30-minute budget (1800 s).  \n"
    "🟢 OPTIMAL  🟠 FEASIBLE (timeout with solution)  🔴 TIMEOUT (no solution)_"
)

with open(REPORT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(lines) + "\n")
print(f"Wrote {REPORT_MD}")

# ─── 8. Generate scalability plot ────────────────────────────────────────────
if scale_rows and any(r.get("solve_time") is not None for r in scale_rows):
    valid = [r for r in scale_rows if r.get("solve_time") is not None]
    sizes    = [r["n_tasks"]    for r in valid]
    times    = [r["solve_time"] for r in valid]
    statuses = [r["status"]     for r in valid]

    color_map = {"OPTIMAL": "tab:green", "FEASIBLE": "tab:orange"}
    colors = [color_map.get(s, "tab:red") for s in statuses]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(sizes, times, color="steelblue", linewidth=1.5, zorder=3, alpha=0.7)
    ax.scatter(sizes, times, c=colors, s=120, zorder=5, edgecolors="white", linewidths=0.8)

    # Annotate each point
    for sz, t, s in zip(sizes, times, statuses):
        ax.annotate(s, (sz, t),
                    textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=8, fontweight="bold")

    # 30-min budget line
    ax.axhline(1800, color="crimson", linestyle="--", linewidth=1.4,
               label="30-min budget (1800 s)", zorder=4)

    legend_els = [
        Patch(color="tab:green",  label="OPTIMAL"),
        Patch(color="tab:orange", label="FEASIBLE (best solution at timeout)"),
        Patch(color="tab:red",    label="TIMEOUT (no feasible solution)"),
        plt.Line2D([0], [0], color="crimson", linestyle="--", label="30-min budget"),
    ]
    ax.legend(handles=legend_els, fontsize=8, loc="upper left")

    ax.set_xlabel("Number of Tasks (N)", fontsize=11)
    ax.set_ylabel("Solve Time (s)", fontsize=11)
    ax.set_title("CP-SAT ILP Scalability: Solve Time vs Task Count\n(pai_full.json sample, seed=42)",
                 fontsize=11)
    ax.set_yscale("log")
    ax.set_ylim(bottom=0.1)
    ax.grid(True, alpha=0.25)
    ax.set_xticks(sizes)

    plt.tight_layout()
    plt.savefig(PLOT_PNG, dpi=150)
    plt.close()
    print(f"Wrote {PLOT_PNG}")
else:
    print("No scalability data with timing yet — skipping plot.")

# ─── 9. Console sanity check ─────────────────────────────────────────────────
print("\n=== Sanity Check ===")
print(f"No-Packing baseline: NaiveScheduler = ${naive_cost:,.2f}")
print("\nSimulation results (cheapest to most expensive):")
for r in sorted(sim_data, key=lambda x: x["total cost"]):
    pct = (r["total cost"] / naive_cost) * 100
    print(f"  {r['scheduler name']:<25}  ${r['total cost']:>10,.2f}  ({pct:.1f}% of No-Packing)")

if cpsat_200 and cpsat_200.get("total cost"):
    c = cpsat_200["total cost"]
    pct = (c / naive_cost) * 100
    print(f"  {'CP-SAT (ILP)':<25}  ${c:>10,.2f}  ({pct:.1f}% of No-Packing)  [{cpsat_200.get('solve_status')}]")
