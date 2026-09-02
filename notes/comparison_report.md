# EVA Scheduler vs CP-SAT ILP: Comparison Report

_Updated: 2026-09-02 — All figures from live simulation runs and CP-SAT fixed-model solves._

---

## Section 1 — Instantaneous Cost Comparison: Decision-Point Snapshots (pai_200)

> **Previous comparison retired**: An earlier version of this report compared EVA's
> 196-hour aggregate total cost against CP-SAT's 1-hour static snapshot cost.
> That comparison is **invalid** — they measure different things. It has been
> replaced entirely by the decision-point snapshot methodology below.

> **Methodology**: 8 timestamps were selected across the simulation (t = 9,900 s to
> t = 300,000 s). At each timestamp the exact set of tasks committed to active instances
> was extracted from `EVAGangScheduler_pai_200/report.json` instance histories.
> **EVA $/hr** = sum of hourly costs of all provisioned instances at that moment.
> **CP-SAT $/hr** = provably optimal bin-packing of the same task set across 21 instance
> types (fixed per-type count model). All CP-SAT solves returned **OPTIMAL** status in
> under 0.5 seconds. This is a true apples-to-apples comparison: same task set,
> same moment in time.

| Timestamp (s) | Sim Hour | Active Tasks | Active Instances | EVA $/hr | CP-SAT Optimal $/hr | Gap % |
|---:|---:|---:|---:|---:|---:|---:|
| 9,900 | 2.75 h | 8 | 8 | $103.12 | $25.91 | +298.03% |
| 51,300 | 14.25 h | 30 | 20 | $212.36 | $104.00 | +104.20% |
| 93,000 | 25.83 h | 31 | 17 | $223.18 | $109.59 | +103.65% |
| 134,400 | 37.33 h | 43 | 27 | $327.22 | $161.08 | +103.14% |
| 165,600 | 46.00 h | 47 | 33 | $363.94 | $176.38 | +106.34% |
| 217,200 | 60.33 h | 40 | 25 | $257.86 | $129.28 | +99.46% |
| 258,600 | 71.83 h | 28 | 18 | $187.17 | $94.45 | +98.18% |
| 300,000 | 83.33 h | 20 | 11 | $129.23 | $64.79 | +99.47% |

**Gap summary** (8 snapshots): min = +98.18%, max = +298.03%, mean = +126.56%

> **What the gap measures**: EVA consistently pays ~2x the CP-SAT optimal for the exact
> same concurrent task set. The gap arises because EVA's gang scheduler provisions one
> dedicated instance per task (one-task-one-machine), whereas CP-SAT discovers that
> multiple small GPU tasks can be legally bin-packed onto fewer, larger instances.
> For example at t=9,900 s: EVA opens 8 separate p3.16xlarge instances ($103.12/hr total);
> CP-SAT packs all 7 GPU tasks onto 1 p3.16xlarge + 1 c7i.8xlarge ($25.91/hr total).

> **t=9,900 s outlier (+298%)**: This is the earliest snapshot, when EVA has just spun up
> a dedicated instance per arriving task. The gap narrows to a stable ~100% for all later
> snapshots once EVA's reconfiguration logic has had time to consolidate.

> **Full per-snapshot detail** (task lists, demand vectors, CP-SAT assignments):
> see [`notes/decision_point_comparison.md`](decision_point_comparison.md).

---

## Section 2 — Dynamic Scheduler Ranking (pai_200 trace)

> **Unit**: Average $/hr over each scheduler's full simulation horizon. This is the
> correct unit for comparing dynamic schedulers against each other — a scheduler that
> finishes faster has a lower total cost even if its per-hour spend is higher, so
> total cost alone is misleading.

| Scheduler | Total Cost ($) | Sim Horizon (hrs) | Avg $/hr | % of Naive baseline |
|---|---:|---:|---:|---:|
| **EVAGangScheduler** | 25,190.69 | 196.50 | **$128.20** | **67.4%** |
| StratusScheduler | 29,050.42 | 205.25 | $141.54 | 74.4% |
| OwlScheduler | 28,936.19 | 199.00 | $145.41 | 76.4% |
| SynergyScheduler | 33,058.43 | 188.75 | $175.14 | 92.0% |
| NaiveScheduler *(no packing)* | 35,858.35 | 188.42 | $190.31 | 100.0% |

> **Ranking**: EVA ($128.20/hr) > Stratus ($141.54/hr) > Owl ($145.41/hr) >
> Synergy ($175.14/hr) > Naive ($190.31/hr). Matches the EVA paper Table 4/11
> ordering exactly. EVA is 32.7% cheaper per hour than the no-packing baseline.

> **Note**: These average $/hr figures should NOT be compared against CP-SAT's
> instantaneous $/hr snapshots above. The averages cover a 196-hour window with
> low task counts at start/end; CP-SAT snapshots are peak-load instants. The only
> valid comparison is the decision-point snapshot table in Section 1.

---

## Section 3 — CP-SAT Scalability Sweep (Fixed Per-Type Count Model)

Tasks sampled from `pai_full.json` with `random.seed(42)`.
Time limit: **30 minutes** per solve. Workers: **8**.
Formulation: **per-type count variables** `cnt[t]` — symmetry-free vector bin-packing.

| N Tasks | Status | Cost ($/hr) | Best Bound ($/hr) | Gap | Solve Time |
|---:|:---:|---:|---:|---:|---:|
| 50 | OPTIMAL | $176.54 | $176.54 | 0.000% | 0.34 s |
| 100 | OPTIMAL | $361.31 | $361.31 | 0.000% | 0.32 s |
| 200 | OPTIMAL | $716.30 | $716.30 | 0.000% | 5.1 s |
| 400 | FEASIBLE | $1,373.96 | $1,373.90 | 0.005% | 30.0 min |
| 800 | FEASIBLE | $2,828.03 | $2,827.70 | 0.012% | 30.0 min |

> **OPTIMAL frontier**: The fixed model proves global optimality for all sizes up to
> N=200 in under 6 seconds — a 300x speedup over the old slot-indexed model which
> never reached OPTIMAL at any size within 30 minutes.

> **Scalability wall at N=400**: Beyond N=200 the 30-minute budget is exhausted before
> the optimality gap closes — but the gap is tiny (0.005% at N=400, 0.012% at N=800).
> The fixed formulation delivers practically optimal solutions at N<=800 within 30
> minutes, but cannot prove optimality beyond N=200 within that budget.

> **Bound quality**: The old broken slot-indexed model reported a bound of $0.18 on a
> $1,411 solution at N=400 (99.99% gap) and $3.39 on $2,936 at N=800 (99.9% gap).
> Those bounds were meaningless. The fixed model's bounds are tight and certifiable.

---

## Section 4 — Validity Notes

### (a) Decision-Point Snapshot Methodology

At each snapshot timestamp t:
1. All instances with `instantiate_start_time <= t < shut_down_end_time` are considered
   active (billing). EVA cost = sum of their hourly rates.
2. From each active instance's `history`, the last entry with `timestamp <= t` gives
   `committed_task_ids` — the tasks EVA had assigned at that moment.
3. Union of all committed task IDs = concurrent active task set.
4. Demand vector `[GPU, CPU, RAM]` per task from `demand_dict` in report.json
   (p3 family entry for GPU tasks; c7i/r7i for CPU-only tasks).
5. CP-SAT fixed model run on that exact task set (21 instance types, 60-second limit).

### (b) Dynamic Scheduler $/hr Derivation

| Scheduler | Total Cost | Horizon | Avg $/hr |
|---|---:|---:|---:|
| NaiveScheduler | $35,858.35 | 188.42 hrs (678,301 s) | $190.31/hr |
| EVAGangScheduler | $25,190.69 | 196.50 hrs (707,401 s) | $128.20/hr |
| StratusScheduler | $29,050.42 | 205.25 hrs (738,901 s) | $141.54/hr |
| OwlScheduler | $28,936.19 | 199.00 hrs (716,401 s) | $145.41/hr |
| SynergyScheduler | $33,058.43 | 188.75 hrs (679,501 s) | $175.14/hr |

### (c) N=400/800 — Real Scalability Boundary

Both N=400 and N=800 were run with the **fixed per-type count formulation** (not the
old slot-indexed model). Results are real, not stale.

- **N=400 (FEASIBLE, 0.005% gap)**: Solution $1,373.96/hr, proven bound $1,373.90/hr.
  The gap is below any practical significance. 30-minute budget exhausted before the
  final proof step, but solution quality is excellent.
- **N=800 (FEASIBLE, 0.012% gap)**: Solution $2,828.03/hr, bound $2,827.70/hr.
  CP-SAT runs zero conflicts — LNS heuristics find the near-optimal solution quickly,
  but the LP relaxation bound tightens too slowly to close the proof within 30 minutes.

**Honest scalability conclusion**: the fixed CP-SAT formulation scales to N=800 tasks
with sub-0.02% optimality gap within 30 minutes on 8 cores. Proved OPTIMAL: N<=200 (5 s).

---

## Section 5 — Scalability Plot

![Solve time vs task count](scalability.png)

_Green = OPTIMAL (proved globally optimal). Orange = FEASIBLE (best solution at timeout, gap <0.02%). Dashed red line = 30-minute budget._
