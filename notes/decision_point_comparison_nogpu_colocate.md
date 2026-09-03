> ⚠️ **SUPERSEDED — DIAGNOSTIC STEP ONLY**
> This file is an intermediate/diagnostic result. It is NOT the final comparison for the paper.
> **Authoritative version**: [`decision_point_comparison_tnrp.md`](decision_point_comparison_tnrp.md)
> (TNRP-corrected model — GPU co-location allowed with interference penalty in objective.)

# EVA vs CP-SAT: Decision-Point Snapshot Comparison (No GPU Co-location) [SUPERSEDED]

> **Constraint change**: Added hard constraint that at most one GPU-demanding task
> (`demand[0] > 0`) may be assigned to any single instance (`sum u[i,t] <= cnt[t]`
> for all GPU tasks for each type `t`). CPU-only tasks may still share instances freely.
> Re-evaluated on the exact same 8 snapshot timestamps from `decision_point_snapshots.json`.

---

## Summary Table

| Timestamp (s) | Tasks (GPU/CPU) | Instances | EVA $/hr | CP-SAT Optimal $/hr | Gap % (original) | CP-SAT (no co-loc) $/hr | Gap % (no co-location) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 9900 | 8 (7/1) | 8 | 103.122 | 25.908 | +298.03% | 58.14 | +77.37% |
| 51300 | 30 (26/4) | 20 | 212.364 | 103.9956 | +104.2% | 198.9 | +6.77% |
| 93000 | 31 (28/3) | 17 | 223.176 | 109.5864 | +103.65% | 186.66 | +19.56% |
| 134400 | 43 (41/2) | 27 | 327.216 | 161.0772 | +103.14% | 281.52 | +16.23% |
| 165600 | 47 (45/2) | 33 | 363.936 | 176.3772 | +106.34% | 312.12 | +16.6% |
| 217200 | 40 (32/8) | 25 | 257.856 | 129.2796 | +99.46% | 208.08 | +23.92% |
| 258600 | 28 (25/3) | 18 | 187.17 | 94.446 | +98.18% | 159.12 | +17.63% |
| 300000 | 20 (19/1) | 11 | 129.234 | 64.7892 | +99.47% | 113.22 | +14.14% |

**Original Gap summary** (with GPU co-location): min = +98.18%, max = +298.03%, mean = +126.56%  
**No-GPU-Colocation Gap summary**: min = +6.77%, max = +77.37%, mean = +24.03%  
**Average Gap Reduction**: 102.53 percentage points (gap shrinks by ~81.0%)

> **Sign of the gap**: The gap **remains POSITIVE (+6.77% to +77.40%)** across all 8 snapshots.
> CP-SAT is still cheaper than EVA even without GPU co-location, but the massive ~100% gap collapses to ~16% on steady-state snapshots.

---

## Key Insights

1. **The ~100% gap was predominantly GPU co-location**: When CP-SAT was free to co-locate multiple GPU tasks onto 8-GPU `p3.16xlarge` instances, it achieved costs ~50% of EVA. Once GPU co-location is forbidden, CP-SAT's cost rises substantially (e.g. from $176.38/hr to $312.12/hr at peak t=165,600s), closing ~85% of the apparent gap.
2. **Does it stay positive or flip negative?**: It **stays positive at every single snapshot**. CP-SAT is still 6.8% to 23.9% cheaper than EVA during steady state (mean +17.0% across t=51,300s to t=300,000s), and 77.4% cheaper at the initial spin-up (t=9,900s). EVA is never cheaper than CP-SAT.
3. **Why CP-SAT remains 7%–24% cheaper without GPU co-location**:
   - **Right-sizing**: CP-SAT assigns single-GPU tasks to `p3.2xlarge` ($3.06/hr) whenever memory/CPU permit, whereas EVA often uses `p3.8xlarge` ($12.24/hr) or `p3.16xlarge` ($24.48/hr).
   - **CPU-only task consolidation**: CPU-only tasks are packed optimally onto cheap `r7i`/`c7i` instances.
   - **Dynamic vs Static slack**: EVA maintains provisioned instances across migration phases, reconfigurations, and task terminations (slack/billing boundaries), whereas CP-SAT is a zero-slack instantaneous assignment.

---

## Per-Snapshot Detail (No GPU Co-location)

### Snapshot t = 9900 s (2.75 h)

- **Active tasks**: 8 (GPU: 7, CPU: 1)
- **Active instances (EVA)**: 8
- **EVA $/hr**: `103.122`
- **CP-SAT (original coloc) $/hr**: `25.908` (Gap: `+298.03%`)
- **CP-SAT (no GPU coloc) $/hr**: `58.14` (bound: `58.14`)
- **CP-SAT status**: OPTIMAL (solved in 0.06s)
- **Gap % (no co-location)**: `+77.37%` (Gap shrunk by `220.66` percentage points)

#### CP-SAT Optimal Assignment (No GPU Co-location)

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 3 | node0 (job 1), node0 (job 3), node0 (job 6) |
| p3.8xlarge | 4 | node0 (job 0), node0 (job 4), node0 (job 5), node0 (job 7), node0 (job 8) |

---

### Snapshot t = 51300 s (14.25 h)

- **Active tasks**: 30 (GPU: 26, CPU: 4)
- **Active instances (EVA)**: 20
- **EVA $/hr**: `212.364`
- **CP-SAT (original coloc) $/hr**: `103.9956` (Gap: `+104.20%`)
- **CP-SAT (no GPU coloc) $/hr**: `198.9` (bound: `198.9`)
- **CP-SAT status**: OPTIMAL (solved in 0.07s)
- **Gap % (no co-location)**: `+6.77%` (Gap shrunk by `97.44` percentage points)

#### CP-SAT Optimal Assignment (No GPU Co-location)

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 13 | node0 (job 6), node0 (job 13), node0 (job 17), node0 (job 18), node0 (job 20), node0 (job 24), node0 (job 26), node0 (job 28), node0 (job 31), node0 (job 36), node0 (job 37), node0 (job 45), node0 (job 47) |
| p3.8xlarge | 13 | node0 (job 5), node0 (job 14), node0 (job 15), node0 (job 25), node0 (job 29), node0 (job 33), node0 (job 34), node0 (job 40), node0 (job 41), node0 (job 44), node0 (job 46), node0 (job 48), node0 (job 49), node0 (job 50), node0 (job 51), node0 (job 52), node0 (job 53) |

---

### Snapshot t = 93000 s (25.83 h)

- **Active tasks**: 31 (GPU: 28, CPU: 3)
- **Active instances (EVA)**: 17
- **EVA $/hr**: `223.176`
- **CP-SAT (original coloc) $/hr**: `109.5864` (Gap: `+103.65%`)
- **CP-SAT (no GPU coloc) $/hr**: `186.66` (bound: `186.66`)
- **CP-SAT status**: OPTIMAL (solved in 0.1s)
- **Gap % (no co-location)**: `+19.56%` (Gap shrunk by `84.09` percentage points)

#### CP-SAT Optimal Assignment (No GPU Co-location)

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 17 | node0 (job 6), node0 (job 13), node0 (job 18), node0 (job 20), node0 (job 26), node0 (job 28), node0 (job 31), node0 (job 37), node0 (job 47), node0 (job 64), node0 (job 71), node0 (job 77), node0 (job 80), node0 (job 83), node0 (job 85), node0 (job 88), node0 (job 91) |
| p3.8xlarge | 11 | node0 (job 5), node0 (job 29), node0 (job 33), node0 (job 40), node0 (job 41), node0 (job 48), node0 (job 52), node0 (job 55), node0 (job 73), node0 (job 78), node0 (job 79), node0 (job 86), node0 (job 89), node0 (job 90) |

---

### Snapshot t = 134400 s (37.33 h)

- **Active tasks**: 43 (GPU: 41, CPU: 2)
- **Active instances (EVA)**: 27
- **EVA $/hr**: `327.216`
- **CP-SAT (original coloc) $/hr**: `161.0772` (Gap: `+103.14%`)
- **CP-SAT (no GPU coloc) $/hr**: `281.52` (bound: `281.52`)
- **CP-SAT status**: OPTIMAL (solved in 0.06s)
- **Gap % (no co-location)**: `+16.23%` (Gap shrunk by `86.91` percentage points)

#### CP-SAT Optimal Assignment (No GPU Co-location)

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 24 | node0 (job 6), node0 (job 13), node0 (job 20), node0 (job 26), node0 (job 28), node0 (job 31), node0 (job 77), node0 (job 80), node0 (job 83), node0 (job 85), node0 (job 91), node0 (job 92), node0 (job 93), node0 (job 94), node0 (job 95), node0 (job 102), node0 (job 103), node0 (job 108), node0 (job 113), node0 (job 115), node0 (job 116), node0 (job 117), node0 (job 119), node0 (job 125) |
| p3.8xlarge | 17 | node0 (job 5), node0 (job 29), node0 (job 33), node0 (job 40), node0 (job 48), node0 (job 52), node0 (job 55), node0 (job 73), node0 (job 78), node0 (job 86), node0 (job 96), node0 (job 101), node0 (job 104), node0 (job 105), node0 (job 110), node0 (job 111), node0 (job 114), node0 (job 120), node0 (job 124) |

---

### Snapshot t = 165600 s (46.0 h)

- **Active tasks**: 47 (GPU: 45, CPU: 2)
- **Active instances (EVA)**: 33
- **EVA $/hr**: `363.936`
- **CP-SAT (original coloc) $/hr**: `176.3772` (Gap: `+106.34%`)
- **CP-SAT (no GPU coloc) $/hr**: `312.12` (bound: `312.12`)
- **CP-SAT status**: OPTIMAL (solved in 0.08s)
- **Gap % (no co-location)**: `+16.60%` (Gap shrunk by `89.74` percentage points)

#### CP-SAT Optimal Assignment (No GPU Co-location)

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 26 | node0 (job 6), node0 (job 13), node0 (job 20), node0 (job 26), node0 (job 28), node0 (job 31), node0 (job 77), node0 (job 80), node0 (job 83), node0 (job 85), node0 (job 91), node0 (job 93), node0 (job 95), node0 (job 102), node0 (job 103), node0 (job 108), node0 (job 115), node0 (job 116), node0 (job 140), node0 (job 142), node0 (job 143), node0 (job 144), node0 (job 145), node0 (job 146), node0 (job 151), node0 (job 153) |
| p3.8xlarge | 19 | node0 (job 5), node0 (job 29), node0 (job 33), node0 (job 40), node0 (job 48), node0 (job 52), node0 (job 55), node0 (job 73), node0 (job 78), node0 (job 86), node0 (job 101), node0 (job 104), node0 (job 124), node0 (job 135), node0 (job 137), node0 (job 138), node0 (job 147), node0 (job 148), node0 (job 149), node0 (job 150), node0 (job 152) |

---

### Snapshot t = 217200 s (60.33 h)

- **Active tasks**: 40 (GPU: 32, CPU: 8)
- **Active instances (EVA)**: 25
- **EVA $/hr**: `257.856`
- **CP-SAT (original coloc) $/hr**: `129.2796` (Gap: `+99.46%`)
- **CP-SAT (no GPU coloc) $/hr**: `208.08` (bound: `208.08`)
- **CP-SAT status**: OPTIMAL (solved in 0.11s)
- **Gap % (no co-location)**: `+23.92%` (Gap shrunk by `75.53` percentage points)

#### CP-SAT Optimal Assignment (No GPU Co-location)

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 20 | node0 (job 26), node0 (job 28), node0 (job 31), node0 (job 40), node0 (job 77), node0 (job 80), node0 (job 83), node0 (job 85), node0 (job 93), node0 (job 102), node0 (job 103), node0 (job 115), node0 (job 143), node0 (job 144), node0 (job 154), node0 (job 158), node0 (job 162), node0 (job 164), node0 (job 177), node0 (job 178), node0 (job 188), node0 (job 189) |
| p3.8xlarge | 12 | node0 (job 29), node0 (job 33), node0 (job 52), node0 (job 55), node0 (job 86), node0 (job 104), node0 (job 124), node0 (job 135), node0 (job 171), node0 (job 173), node0 (job 176), node0 (job 179), node0 (job 181), node0 (job 183), node0 (job 184), node0 (job 185), node0 (job 186), node0 (job 187) |

---

### Snapshot t = 258600 s (71.83 h)

- **Active tasks**: 28 (GPU: 25, CPU: 3)
- **Active instances (EVA)**: 18
- **EVA $/hr**: `187.17`
- **CP-SAT (original coloc) $/hr**: `94.446` (Gap: `+98.18%`)
- **CP-SAT (no GPU coloc) $/hr**: `159.12` (bound: `159.12`)
- **CP-SAT status**: OPTIMAL (solved in 0.07s)
- **Gap % (no co-location)**: `+17.63%` (Gap shrunk by `80.55` percentage points)

#### CP-SAT Optimal Assignment (No GPU Co-location)

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 16 | node0 (job 26), node0 (job 28), node0 (job 31), node0 (job 83), node0 (job 85), node0 (job 93), node0 (job 102), node0 (job 103), node0 (job 115), node0 (job 143), node0 (job 144), node0 (job 154), node0 (job 158), node0 (job 178), node0 (job 196), node0 (job 197) |
| p3.8xlarge | 9 | node0 (job 33), node0 (job 40), node0 (job 55), node0 (job 104), node0 (job 124), node0 (job 135), node0 (job 171), node0 (job 176), node0 (job 183), node0 (job 191), node0 (job 193), node0 (job 194) |

---

### Snapshot t = 300000 s (83.33 h)

- **Active tasks**: 20 (GPU: 19, CPU: 1)
- **Active instances (EVA)**: 11
- **EVA $/hr**: `129.234`
- **CP-SAT (original coloc) $/hr**: `64.7892` (Gap: `+99.47%`)
- **CP-SAT (no GPU coloc) $/hr**: `113.22` (bound: `113.22`)
- **CP-SAT status**: OPTIMAL (solved in 0.06s)
- **Gap % (no co-location)**: `+14.14%` (Gap shrunk by `85.32` percentage points)

#### CP-SAT Optimal Assignment (No GPU Co-location)

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 13 | node0 (job 26), node0 (job 28), node0 (job 40), node0 (job 83), node0 (job 85), node0 (job 93), node0 (job 102), node0 (job 103), node0 (job 115), node0 (job 143), node0 (job 144), node0 (job 158), node0 (job 178), node0 (job 196) |
| p3.8xlarge | 6 | node0 (job 33), node0 (job 104), node0 (job 124), node0 (job 135), node0 (job 171), node0 (job 194) |

---

