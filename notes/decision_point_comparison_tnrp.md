# EVA vs CP-SAT: Decision-Point Snapshot Comparison — TNRP-Corrected (AUTHORITATIVE)

> **This is the authoritative version for the paper.**
> Both earlier files (`decision_point_comparison.md` and
> `decision_point_comparison_nogpu_colocate.md`) are intermediate/diagnostic
> steps and should not be cited as final results. See SUPERSEDED headers in those files.

## Methodology

**CP-SAT TNRP-corrected model**:
- GPU tasks *can* share an instance (no hard co-location ban).
- For each pair of GPU tasks assigned to the same instance type, a **TNRP
  interference penalty** is added to the objective:
  ```
  penalty(i,j) = cost(min_it_i) × (1 - rate(i|j))
               + cost(min_it_j) × (1 - rate(j|i))
  ```
  where `rate(i|j)` = EVA's `get_contention_rate(label_i, (label_j,), contention_map)`.
- **Lookup order**: (1) direct contention_map entry for exact tuple,
  (2) pairwise product fallback — matching EVA's own code exactly.
- **Audit result** (Section 8 of `notes/tnrp_formula.md`): 22/22 (100%) of
  3+-GPU-task groups found across all 8 snapshots had **direct** entries in
  `contention_map`. The pairwise fallback introduces no additional inaccuracy
  beyond what EVA's own scheduler already accepts.

---

## Summary Table — All Three CP-SAT Variants vs EVA

| Timestamp (s) | Tasks (GPU/CPU) | EVA $/hr | CP-SAT free-coloc $/hr | Gap % | CP-SAT no-GPU-coloc $/hr | Gap % | **CP-SAT TNRP $/hr** | **Gap %** |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 9900 | 8 (7/1) | 103.1220 | 25.9080 | +298.03% | 58.1400 | +77.37% | **45.2023** | **+128.13%** |
| 51300 | 30 (26/4) | 212.3640 | 103.9956 | +104.20% | 198.9000 | +6.77% | **179.4556** | **+18.34%** |
| 93000 | 31 (28/3) | 223.1760 | 109.5864 | +103.65% | 186.6600 | +19.56% | **175.3580** | **+27.27%** |
| 134400 | 43 (41/2) | 327.2160 | 161.0772 | +103.14% | 281.5200 | +16.23% | **295.7541** | **+10.64%** |
| 165600 | 47 (45/2) | 363.9360 | 176.3772 | +106.34% | 312.1200 | +16.60% | **340.0843** | **+7.01%** |
| 217200 | 40 (32/8) | 257.8560 | 129.2796 | +99.46% | 208.0800 | +23.92% | **219.8405** | **+17.29%** |
| 258600 | 28 (25/3) | 187.1700 | 94.4460 | +98.18% | 159.1200 | +17.63% | **140.2726** | **+33.43%** |
| 300000 | 20 (19/1) | 129.2340 | 64.7892 | +99.47% | 113.2200 | +14.14% | **93.9173** | **+37.60%** |

**Free co-location**: min=+98.18%, max=+298.03%, mean=+126.56%  
**No GPU co-location**: min=+6.77%, max=+77.37%, mean=+24.03%  
**TNRP-corrected (this version)**: min=+7.01%, max=+128.13%, mean=+34.97%  

---

## TNRP Penalty Decomposition

The TNRP objective = instance provisioning cost + throughput interference penalty.
This table shows how much of the CP-SAT TNRP total is interference penalty:

| Timestamp (s) | TNRP total $/hr | Instance cost $/hr | Penalty $/hr | Penalty % of total |
|---:|---:|---:|---:|---:|
| 9900 | 45.2023 | 36.7200 | 8.4823 | 18.8% |
| 51300 | 179.4556 | 109.0572 | 70.3984 | 39.2% |
| 93000 | 175.3580 | 112.6464 | 62.7116 | 35.8% |
| 134400 | 295.7541 | 163.6080 | 132.1461 | 44.7% |
| 165600 | 340.0843 | 181.9680 | 158.1163 | 46.5% |
| 217200 | 219.8405 | 131.8104 | 88.0301 | 40.0% |
| 258600 | 140.2726 | 94.4460 | 45.8266 | 32.7% |
| 300000 | 93.9173 | 64.7892 | 29.1281 | 31.0% |

---

## Per-Snapshot Detail (TNRP-Corrected)

### Snapshot t = 9900 s (2.75 h)

- **Active tasks**: 8 (GPU: 7, CPU: 1)
- **Active instances (EVA)**: 8
- **EVA $/hr**: `103.1220`
- **CP-SAT free co-loc $/hr**: `25.9080` (Gap: `+298.03%`)
- **CP-SAT no-GPU-coloc $/hr**: `58.1400` (Gap: `+77.37%`)
- **CP-SAT TNRP $/hr**: `45.2023` (inst `36.7200` + penalty `8.4823`) — status: OPTIMAL (0.11s)
- **Gap % (TNRP)**: `+128.13%`

#### CP-SAT TNRP Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.8xlarge | 1 | node0 (job 0), node0 (job 1), node0 (job 4) |
| p3.16xlarge | 1 | node0 (job 3), node0 (job 5), node0 (job 6), node0 (job 7), node0 (job 8) |

---

### Snapshot t = 51300 s (14.25 h)

- **Active tasks**: 30 (GPU: 26, CPU: 4)
- **Active instances (EVA)**: 20
- **EVA $/hr**: `212.3640`
- **CP-SAT free co-loc $/hr**: `103.9956` (Gap: `+104.20%`)
- **CP-SAT no-GPU-coloc $/hr**: `198.9000` (Gap: `+6.77%`)
- **CP-SAT TNRP $/hr**: `179.4556` (inst `109.0572` + penalty `70.3984`) — status: FEASIBLE (60.06s)
- **Gap % (TNRP)**: `+18.34%`

#### CP-SAT TNRP Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 11 | node0 (job 6), node0 (job 13), node0 (job 17), node0 (job 18), node0 (job 20), node0 (job 24), node0 (job 28), node0 (job 31), node0 (job 37), node0 (job 41), node0 (job 45), node0 (job 47), node0 (job 49) |
| p3.8xlarge | 2 | node0 (job 36), node0 (job 44), node0 (job 48), node0 (job 50), node0 (job 51), node0 (job 53) |
| p3.16xlarge | 2 | node0 (job 14), node0 (job 15), node0 (job 25), node0 (job 26), node0 (job 29), node0 (job 33), node0 (job 34), node0 (job 46), node0 (job 52) |
| c7i.8xlarge | 1 | node0 (job 5) |
| r7i.2xlarge | 1 | node0 (job 40) |

---

### Snapshot t = 93000 s (25.83 h)

- **Active tasks**: 31 (GPU: 28, CPU: 3)
- **Active instances (EVA)**: 17
- **EVA $/hr**: `223.1760`
- **CP-SAT free co-loc $/hr**: `109.5864` (Gap: `+103.65%`)
- **CP-SAT no-GPU-coloc $/hr**: `186.6600` (Gap: `+19.56%`)
- **CP-SAT TNRP $/hr**: `175.3580` (inst `112.6464` + penalty `62.7116`) — status: FEASIBLE (60.12s)
- **Gap % (TNRP)**: `+27.27%`

#### CP-SAT TNRP Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 12 | node0 (job 13), node0 (job 18), node0 (job 20), node0 (job 31), node0 (job 37), node0 (job 47), node0 (job 64), node0 (job 71), node0 (job 77), node0 (job 83), node0 (job 85), node0 (job 88) |
| p3.8xlarge | 2 | node0 (job 6), node0 (job 26), node0 (job 33), node0 (job 73), node0 (job 89), node0 (job 90) |
| p3.16xlarge | 2 | node0 (job 28), node0 (job 29), node0 (job 48), node0 (job 52), node0 (job 55), node0 (job 78), node0 (job 79), node0 (job 80), node0 (job 86), node0 (job 91) |
| c7i.8xlarge | 1 | node0 (job 5) |
| r7i.2xlarge | 2 | node0 (job 40), node0 (job 41) |

---

### Snapshot t = 134400 s (37.33 h)

- **Active tasks**: 43 (GPU: 41, CPU: 2)
- **Active instances (EVA)**: 27
- **EVA $/hr**: `327.2160`
- **CP-SAT free co-loc $/hr**: `161.0772` (Gap: `+103.14%`)
- **CP-SAT no-GPU-coloc $/hr**: `281.5200` (Gap: `+16.23%`)
- **CP-SAT TNRP $/hr**: `295.7541` (inst `163.6080` + penalty `132.1461`) — status: FEASIBLE (60.27s)
- **Gap % (TNRP)**: `+10.64%`

#### CP-SAT TNRP Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 13 | node0 (job 6), node0 (job 13), node0 (job 20), node0 (job 40), node0 (job 77), node0 (job 83), node0 (job 85), node0 (job 93), node0 (job 94), node0 (job 102), node0 (job 103), node0 (job 108), node0 (job 113), node0 (job 116) |
| p3.8xlarge | 4 | node0 (job 26), node0 (job 29), node0 (job 31), node0 (job 33), node0 (job 52), node0 (job 73), node0 (job 95), node0 (job 110), node0 (job 115), node0 (job 119), node0 (job 120), node0 (job 124) |
| p3.16xlarge | 3 | node0 (job 28), node0 (job 48), node0 (job 55), node0 (job 78), node0 (job 80), node0 (job 86), node0 (job 91), node0 (job 92), node0 (job 96), node0 (job 101), node0 (job 104), node0 (job 105), node0 (job 111), node0 (job 114), node0 (job 117), node0 (job 125) |
| c7i.8xlarge | 1 | node0 (job 5) |

---

### Snapshot t = 165600 s (46.0 h)

- **Active tasks**: 47 (GPU: 45, CPU: 2)
- **Active instances (EVA)**: 33
- **EVA $/hr**: `363.9360`
- **CP-SAT free co-loc $/hr**: `176.3772` (Gap: `+106.34%`)
- **CP-SAT no-GPU-coloc $/hr**: `312.1200` (Gap: `+16.60%`)
- **CP-SAT TNRP $/hr**: `340.0843` (inst `181.9680` + penalty `158.1163`) — status: FEASIBLE (60.22s)
- **Gap % (TNRP)**: `+7.01%`

#### CP-SAT TNRP Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 15 | node0 (job 6), node0 (job 13), node0 (job 20), node0 (job 31), node0 (job 40), node0 (job 77), node0 (job 83), node0 (job 85), node0 (job 93), node0 (job 102), node0 (job 103), node0 (job 108), node0 (job 116), node0 (job 142), node0 (job 143), node0 (job 153) |
| p3.8xlarge | 5 | node0 (job 26), node0 (job 29), node0 (job 33), node0 (job 52), node0 (job 73), node0 (job 95), node0 (job 104), node0 (job 115), node0 (job 124), node0 (job 144), node0 (job 145), node0 (job 148), node0 (job 149), node0 (job 151) |
| p3.16xlarge | 3 | node0 (job 28), node0 (job 48), node0 (job 55), node0 (job 78), node0 (job 80), node0 (job 86), node0 (job 91), node0 (job 101), node0 (job 135), node0 (job 137), node0 (job 138), node0 (job 140), node0 (job 146), node0 (job 147), node0 (job 150), node0 (job 152) |
| c7i.8xlarge | 1 | node0 (job 5) |

---

### Snapshot t = 217200 s (60.33 h)

- **Active tasks**: 40 (GPU: 32, CPU: 8)
- **Active instances (EVA)**: 25
- **EVA $/hr**: `257.8560`
- **CP-SAT free co-loc $/hr**: `129.2796` (Gap: `+99.46%`)
- **CP-SAT no-GPU-coloc $/hr**: `208.0800` (Gap: `+23.92%`)
- **CP-SAT TNRP $/hr**: `219.8405` (inst `131.8104` + penalty `88.0301`) — status: FEASIBLE (60.11s)
- **Gap % (TNRP)**: `+17.29%`

#### CP-SAT TNRP Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 13 | node0 (job 31), node0 (job 40), node0 (job 77), node0 (job 83), node0 (job 85), node0 (job 93), node0 (job 102), node0 (job 103), node0 (job 115), node0 (job 143), node0 (job 154), node0 (job 177), node0 (job 178), node0 (job 189) |
| p3.8xlarge | 3 | node0 (job 26), node0 (job 29), node0 (job 124), node0 (job 144), node0 (job 158), node0 (job 162), node0 (job 171), node0 (job 173), node0 (job 181), node0 (job 188) |
| p3.16xlarge | 2 | node0 (job 28), node0 (job 33), node0 (job 52), node0 (job 55), node0 (job 80), node0 (job 86), node0 (job 104), node0 (job 135), node0 (job 184) |
| r7i.24xlarge | 1 | node0 (job 164), node0 (job 176), node0 (job 179), node0 (job 183), node0 (job 185), node0 (job 186), node0 (job 187) |

---

### Snapshot t = 258600 s (71.83 h)

- **Active tasks**: 28 (GPU: 25, CPU: 3)
- **Active instances (EVA)**: 18
- **EVA $/hr**: `187.1700`
- **CP-SAT free co-loc $/hr**: `94.4460` (Gap: `+98.18%`)
- **CP-SAT no-GPU-coloc $/hr**: `159.1200` (Gap: `+17.63%`)
- **CP-SAT TNRP $/hr**: `140.2726` (inst `94.4460` + penalty `45.8266`) — status: FEASIBLE (60.06s)
- **Gap % (TNRP)**: `+33.43%`

#### CP-SAT TNRP Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 10 | node0 (job 28), node0 (job 83), node0 (job 85), node0 (job 93), node0 (job 102), node0 (job 103), node0 (job 143), node0 (job 154), node0 (job 178), node0 (job 197) |
| p3.8xlarge | 3 | node0 (job 55), node0 (job 104), node0 (job 135), node0 (job 191), node0 (job 193), node0 (job 194), node0 (job 196) |
| p3.16xlarge | 1 | node0 (job 26), node0 (job 31), node0 (job 33), node0 (job 115), node0 (job 124), node0 (job 144), node0 (job 158), node0 (job 171) |
| r7i.2xlarge | 1 | node0 (job 40) |
| r7i.8xlarge | 1 | node0 (job 176), node0 (job 183) |

---

### Snapshot t = 300000 s (83.33 h)

- **Active tasks**: 20 (GPU: 19, CPU: 1)
- **Active instances (EVA)**: 11
- **EVA $/hr**: `129.2340`
- **CP-SAT free co-loc $/hr**: `64.7892` (Gap: `+99.47%`)
- **CP-SAT no-GPU-coloc $/hr**: `113.2200` (Gap: `+14.14%`)
- **CP-SAT TNRP $/hr**: `93.9173` (inst `64.7892` + penalty `29.1281`) — status: OPTIMAL (18.39s)
- **Gap % (TNRP)**: `+37.60%`

#### CP-SAT TNRP Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 5 | node0 (job 83), node0 (job 93), node0 (job 103), node0 (job 143), node0 (job 178) |
| p3.8xlarge | 2 | node0 (job 33), node0 (job 102), node0 (job 115), node0 (job 124), node0 (job 144), node0 (job 158), node0 (job 171) |
| p3.16xlarge | 1 | node0 (job 26), node0 (job 28), node0 (job 85), node0 (job 104), node0 (job 135), node0 (job 194), node0 (job 196) |
| r7i.2xlarge | 1 | node0 (job 40) |

---

