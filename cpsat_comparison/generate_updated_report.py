import os
import json
import sys

# Locate matplotlib from venv
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
HOURLY_COSTS  = "cpsat_comparison/hourly_costs.json"
REPORT_MD     = os.path.join(NOTES_DIR, "comparison_report.md")
PLOT_PNG      = os.path.join(NOTES_DIR, "scalability.png")

os.makedirs(NOTES_DIR, exist_ok=True)

# 1. Load simulation baseline and hourly costs
with open(BASELINE) as f:
    sim_data = json.load(f)

hourly_data = {}
if os.path.exists(HOURLY_COSTS):
    with open(HOURLY_COSTS) as f:
        hourly_data = json.load(f)

# 2. Load CP-SAT 200-task result
cpsat_200 = None
if os.path.exists(CPSAT_RESULTS):
    with open(CPSAT_RESULTS) as f:
        data = json.load(f)
    cpsat_200 = data[0] if data else None

# 3. Load scalability sweep
scale_rows = []
if os.path.exists(SCALE_RESULTS):
    with open(SCALE_RESULTS) as f:
        scale_rows = json.load(f)

# 4. Generate Plot
if scale_rows and any(r.get("solve_time") is not None for r in scale_rows):
    valid = [r for r in scale_rows if r.get("solve_time") is not None]
    sizes    = [r["n_tasks"]    for r in valid]
    times    = [r["solve_time"] for r in valid]
    statuses = [r["status"]     for r in valid]

    color_map = {"OPTIMAL": "#2ca02c", "FEASIBLE": "#ff7f0e", "TIMEOUT": "#d62728"}
    colors = [color_map.get(s, "#7f7f7f") for s in statuses]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot(sizes, times, color="steelblue", linewidth=1.8, zorder=3, alpha=0.8, linestyle="-")
    ax.scatter(sizes, times, c=colors, s=140, zorder=5, edgecolors="black", linewidths=1.0)

    for sz, t, s in zip(sizes, times, statuses):
        label = f"{s}\n({t:.1f}s)" if t < 60 else f"{s}\n({t/60:.1f}m)"
        offset_y = 12 if t < 1000 else -25
        ax.annotate(label, (sz, t),
                    textcoords="offset points", xytext=(0, offset_y),
                    ha="center", fontsize=8.5, fontweight="bold",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray", alpha=0.7, lw=0.5))

    ax.axhline(1800, color="crimson", linestyle="--", linewidth=1.5,
               label="30-min time limit (1800 s)", zorder=4)

    legend_els = [
        Patch(facecolor="#2ca02c", edgecolor="black", label="OPTIMAL (proved globally optimal)"),
        Patch(facecolor="#ff7f0e", edgecolor="black", label="FEASIBLE (best solution at timeout)"),
        plt.Line2D([0], [0], color="crimson", linestyle="--", linewidth=1.5, label="30-min budget (1800 s)"),
    ]
    ax.legend(handles=legend_els, fontsize=9, loc="upper left", framealpha=0.9)

    ax.set_xlabel("Number of Tasks (N)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Solve Time (s) [Log Scale]", fontsize=11, fontweight="bold")
    ax.set_title("CP-SAT Vector Bin-Packing Scalability: Solve Time vs Task Count\n(Fixed Per-Type Count Formulation, 8 Workers)",
                 fontsize=11.5, fontweight="bold")
    ax.set_yscale("log")
    ax.set_ylim(bottom=0.05, top=5000)
    ax.grid(True, which="both", linestyle=":", alpha=0.5)
    ax.set_xticks(sizes)

    plt.tight_layout()
    plt.savefig(PLOT_PNG, dpi=200)
    plt.close()
    print(f"Generated {PLOT_PNG}")

print("Plot updated successfully.")
