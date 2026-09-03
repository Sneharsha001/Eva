> ⚠️ **SUPERSEDED — DIAGNOSTIC STEP ONLY**
> This file used a CP-SAT model that allowed unrestricted GPU co-location (no interference penalty).
> That produced an artificially low CP-SAT cost (~50% of EVA) by stacking multiple GPU tasks on 8-GPU instances without throughput penalty.
> **Authoritative version**: [`decision_point_comparison_tnrp.md`](decision_point_comparison_tnrp.md)
> (TNRP-corrected model — GPU co-location allowed with EVA’s own interference penalty in objective.)

# EVA vs CP-SAT: Decision-Point Snapshot Comparison (pai_200) [SUPERSEDED]

> **Methodology**: For each snapshot timestamp we determine the exact set of tasks
> that EVA committed to active instances (from report.json instance histories).
> EVA cost = sum of $/hr for all provisioned instances at that moment.
> CP-SAT cost = optimal bin-packing of the same task set across 21 instance types.
> This is a true apples-to-apples comparison: same task set, same moment in time.

---

## Summary Table

| Timestamp (s) | Tasks | Instances | EVA $/hr | CP-SAT Optimal $/hr | Gap % |
|---:|---:|---:|---:|---:|---:|
| 9900 | 8 | 8 | 103.122 | 25.908 | +298.03% |
| 51300 | 30 | 20 | 212.364 | 103.9956 | +104.2% |
| 93000 | 31 | 17 | 223.176 | 109.5864 | +103.65% |
| 134400 | 43 | 27 | 327.216 | 161.0772 | +103.14% |
| 165600 | 47 | 33 | 363.936 | 176.3772 | +106.34% |
| 217200 | 40 | 25 | 257.856 | 129.2796 | +99.46% |
| 258600 | 28 | 18 | 187.17 | 94.446 | +98.18% |
| 300000 | 20 | 11 | 129.234 | 64.7892 | +99.47% |

**Gap summary** across 8 snapshots: min = 98.18%, max = 298.03%, mean = 126.56%

> Positive gap = EVA costs more than CP-SAT optimal for this task set.
> Negative gap = EVA uses fewer/cheaper instances for this task set.

---

## Per-Snapshot Detail

### Snapshot t = 9900 s (2.75 h)

- **Active tasks**: 8
- **Active instances (EVA)**: 8
- **EVA $/hr**: 103.122
- **CP-SAT optimal $/hr**: 25.908 (bound: 25.908)
- **CP-SAT status**: OPTIMAL (solved in 0.13s)
- **Gap**: +298.03%

#### Task Set and EVA Assignment

| Task ID | Name | GPU | CPU | RAM | EVA Instance Type |
|---:|---|---:|---:|---:|---|
| 0 | node0 (job 0) | 1 | 12 | 16 | p3.16xlarge |
| 1 | node0 (job 1) | 1 | 6 | 12 | p3.16xlarge |
| 3 | node0 (job 3) | 1 | 6 | 12 | p3.16xlarge |
| 4 | node0 (job 4) | 1 | 12 | 16 | p3.16xlarge |
| 5 | node0 (job 5) | 0 | 20 | 64 | c7i.12xlarge |
| 6 | node0 (job 6) | 1 | 4 | 16 | p3.2xlarge |
| 7 | node0 (job 7) | 1 | 12 | 16 | p3.16xlarge |
| 8 | node0 (job 8) | 1 | 12 | 16 | p3.16xlarge |

#### CP-SAT Optimal Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.16xlarge | 1 | node0 (job 0), node0 (job 1), node0 (job 3), node0 (job 4), node0 (job 6), node0 (job 7), node0 (job 8) |
| c7i.8xlarge | 1 | node0 (job 5) |

---

### Snapshot t = 51300 s (14.25 h)

- **Active tasks**: 30
- **Active instances (EVA)**: 20
- **EVA $/hr**: 212.364
- **CP-SAT optimal $/hr**: 103.9956 (bound: 103.9956)
- **CP-SAT status**: OPTIMAL (solved in 0.15s)
- **Gap**: +104.2%

#### Task Set and EVA Assignment

| Task ID | Name | GPU | CPU | RAM | EVA Instance Type |
|---:|---|---:|---:|---:|---|
| 5 | node0 (job 5) | 0 | 20 | 64 | c7i.12xlarge |
| 6 | node0 (job 6) | 1 | 4 | 16 | p3.8xlarge |
| 13 | node0 (job 13) | 1 | 8 | 16 | p3.16xlarge |
| 14 | node0 (job 14) | 1 | 16 | 64 | p3.8xlarge |
| 15 | node0 (job 15) | 1 | 16 | 48 | p3.8xlarge |
| 17 | node0 (job 17) | 1 | 6 | 6 | p3.16xlarge |
| 18 | node0 (job 18) | 1 | 8 | 30 | p3.16xlarge |
| 20 | node0 (job 20) | 1 | 8 | 30 | p3.8xlarge |
| 24 | node0 (job 24) | 1 | 4 | 15 | p3.16xlarge |
| 25 | node0 (job 25) | 1 | 16 | 32 | p3.8xlarge |
| 26 | node0 (job 26) | 1 | 1 | 2 | p3.8xlarge |
| 28 | node0 (job 28) | 1 | 4 | 15 | p3.8xlarge |
| 29 | node0 (job 29) | 1 | 16 | 32 | p3.8xlarge |
| 31 | node0 (job 31) | 1 | 6 | 12 | p3.16xlarge |
| 33 | node0 (job 33) | 1 | 16 | 32 | p3.8xlarge |
| 34 | node0 (job 34) | 1 | 16 | 32 | p3.8xlarge |
| 36 | node0 (job 36) | 1 | 4 | 15 | p3.8xlarge |
| 37 | node0 (job 37) | 1 | 8 | 30 | p3.8xlarge |
| 40 | node0 (job 40) | 0 | 8 | 30 | c7i.4xlarge |
| 41 | node0 (job 41) | 0 | 8 | 30 | c7i.4xlarge |
| 44 | node0 (job 44) | 1 | 12 | 16 | p3.8xlarge |
| 45 | node0 (job 45) | 1 | 4 | 24 | p3.8xlarge |
| 46 | node0 (job 46) | 1 | 12 | 48 | p3.8xlarge |
| 47 | node0 (job 47) | 1 | 8 | 16 | p3.8xlarge |
| 48 | node0 (job 48) | 1 | 12 | 46 | p3.8xlarge |
| 49 | node0 (job 49) | 0 | 8 | 30 | c7i.4xlarge |
| 50 | node0 (job 50) | 1 | 12 | 46 | p3.8xlarge |
| 51 | node0 (job 51) | 1 | 12 | 24 | p3.8xlarge |
| 52 | node0 (job 52) | 1 | 16 | 32 | p3.8xlarge |
| 53 | node0 (job 53) | 1 | 12 | 16 | p3.8xlarge |

#### CP-SAT Optimal Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 1 | node0 (job 47) |
| p3.8xlarge | 2 | node0 (job 13), node0 (job 14), node0 (job 15), node0 (job 17), node0 (job 28), node0 (job 36), node0 (job 37) |
| p3.16xlarge | 3 | node0 (job 6), node0 (job 18), node0 (job 20), node0 (job 24), node0 (job 25), node0 (job 26), node0 (job 29), node0 (job 31), node0 (job 33), node0 (job 34), node0 (job 44), node0 (job 45), node0 (job 46), node0 (job 48), node0 (job 50), node0 (job 51), node0 (job 52), node0 (job 53) |
| c7i.8xlarge | 1 | node0 (job 5) |
| r7i.2xlarge | 3 | node0 (job 40), node0 (job 41), node0 (job 49) |

---

### Snapshot t = 93000 s (25.83 h)

- **Active tasks**: 31
- **Active instances (EVA)**: 17
- **EVA $/hr**: 223.176
- **CP-SAT optimal $/hr**: 109.5864 (bound: 109.5864)
- **CP-SAT status**: OPTIMAL (solved in 0.14s)
- **Gap**: +103.65%

#### Task Set and EVA Assignment

| Task ID | Name | GPU | CPU | RAM | EVA Instance Type |
|---:|---|---:|---:|---:|---|
| 5 | node0 (job 5) | 0 | 20 | 64 | c7i.12xlarge |
| 6 | node0 (job 6) | 1 | 4 | 16 | p3.8xlarge |
| 13 | node0 (job 13) | 1 | 8 | 16 | p3.8xlarge |
| 18 | node0 (job 18) | 1 | 8 | 30 | p3.16xlarge |
| 20 | node0 (job 20) | 1 | 8 | 30 | p3.16xlarge |
| 26 | node0 (job 26) | 1 | 1 | 2 | p3.16xlarge |
| 28 | node0 (job 28) | 1 | 4 | 15 | p3.16xlarge |
| 29 | node0 (job 29) | 1 | 16 | 32 | p3.8xlarge |
| 31 | node0 (job 31) | 1 | 6 | 12 | p3.8xlarge |
| 33 | node0 (job 33) | 1 | 16 | 32 | p3.8xlarge |
| 37 | node0 (job 37) | 1 | 8 | 30 | p3.8xlarge |
| 40 | node0 (job 40) | 0 | 8 | 30 | p3.8xlarge |
| 41 | node0 (job 41) | 0 | 8 | 30 | c7i.4xlarge |
| 47 | node0 (job 47) | 1 | 8 | 16 | p3.8xlarge |
| 48 | node0 (job 48) | 1 | 12 | 46 | p3.16xlarge |
| 52 | node0 (job 52) | 1 | 16 | 32 | p3.8xlarge |
| 55 | node0 (job 55) | 1 | 19 | 63 | p3.16xlarge |
| 64 | node0 (job 64) | 1 | 5 | 11 | p3.16xlarge |
| 71 | node0 (job 71) | 1 | 8 | 30 | p3.8xlarge |
| 73 | node0 (job 73) | 1 | 16 | 57 | p3.8xlarge |
| 77 | node0 (job 77) | 1 | 8 | 30 | p3.8xlarge |
| 78 | node0 (job 78) | 1 | 19 | 63 | p3.16xlarge |
| 79 | node0 (job 79) | 1 | 19 | 63 | p3.16xlarge |
| 80 | node0 (job 80) | 1 | 4 | 15 | p3.8xlarge |
| 83 | node0 (job 83) | 1 | 8 | 30 | p3.8xlarge |
| 85 | node0 (job 85) | 1 | 8 | 30 | p3.8xlarge |
| 86 | node0 (job 86) | 1 | 12 | 32 | p3.8xlarge |
| 88 | node0 (job 88) | 1 | 8 | 30 | p3.8xlarge |
| 89 | node0 (job 89) | 1 | 12 | 24 | p3.8xlarge |
| 90 | node0 (job 90) | 1 | 12 | 15 | p3.8xlarge |
| 91 | node0 (job 91) | 1 | 4 | 15 | p3.8xlarge |

#### CP-SAT Optimal Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 3 | node0 (job 13), node0 (job 18), node0 (job 47) |
| p3.16xlarge | 4 | node0 (job 6), node0 (job 20), node0 (job 26), node0 (job 28), node0 (job 29), node0 (job 31), node0 (job 33), node0 (job 37), node0 (job 48), node0 (job 52), node0 (job 55), node0 (job 64), node0 (job 71), node0 (job 73), node0 (job 77), node0 (job 78), node0 (job 79), node0 (job 80), node0 (job 83), node0 (job 85), node0 (job 86), node0 (job 88), node0 (job 89), node0 (job 90), node0 (job 91) |
| c7i.8xlarge | 1 | node0 (job 5) |
| r7i.4xlarge | 1 | node0 (job 40), node0 (job 41) |

---

### Snapshot t = 134400 s (37.33 h)

- **Active tasks**: 43
- **Active instances (EVA)**: 27
- **EVA $/hr**: 327.216
- **CP-SAT optimal $/hr**: 161.0772 (bound: 161.0772)
- **CP-SAT status**: OPTIMAL (solved in 0.13s)
- **Gap**: +103.14%

#### Task Set and EVA Assignment

| Task ID | Name | GPU | CPU | RAM | EVA Instance Type |
|---:|---|---:|---:|---:|---|
| 5 | node0 (job 5) | 0 | 20 | 64 | c7i.12xlarge |
| 6 | node0 (job 6) | 1 | 4 | 16 | p3.2xlarge |
| 13 | node0 (job 13) | 1 | 8 | 16 | p3.8xlarge |
| 20 | node0 (job 20) | 1 | 8 | 30 | p3.16xlarge |
| 26 | node0 (job 26) | 1 | 1 | 2 | p3.16xlarge |
| 28 | node0 (job 28) | 1 | 4 | 15 | p3.16xlarge |
| 29 | node0 (job 29) | 1 | 16 | 32 | p3.8xlarge |
| 31 | node0 (job 31) | 1 | 6 | 12 | p3.8xlarge |
| 33 | node0 (job 33) | 1 | 16 | 32 | p3.8xlarge |
| 40 | node0 (job 40) | 0 | 8 | 30 | c7i.4xlarge |
| 48 | node0 (job 48) | 1 | 12 | 46 | p3.16xlarge |
| 52 | node0 (job 52) | 1 | 16 | 32 | p3.8xlarge |
| 55 | node0 (job 55) | 1 | 19 | 63 | p3.16xlarge |
| 73 | node0 (job 73) | 1 | 16 | 57 | p3.8xlarge |
| 77 | node0 (job 77) | 1 | 8 | 30 | p3.16xlarge |
| 78 | node0 (job 78) | 1 | 19 | 63 | p3.16xlarge |
| 80 | node0 (job 80) | 1 | 4 | 15 | p3.16xlarge |
| 83 | node0 (job 83) | 1 | 8 | 30 | p3.8xlarge |
| 85 | node0 (job 85) | 1 | 8 | 30 | p3.8xlarge |
| 86 | node0 (job 86) | 1 | 12 | 32 | p3.16xlarge |
| 91 | node0 (job 91) | 1 | 4 | 15 | p3.16xlarge |
| 92 | node0 (job 92) | 1 | 4 | 15 | p3.2xlarge |
| 93 | node0 (job 93) | 1 | 8 | 30 | p3.8xlarge |
| 94 | node0 (job 94) | 1 | 8 | 30 | p3.8xlarge |
| 95 | node0 (job 95) | 1 | 4 | 24 | p3.2xlarge |
| 96 | node0 (job 96) | 1 | 19 | 63 | p3.16xlarge |
| 101 | node0 (job 101) | 1 | 19 | 63 | p3.16xlarge |
| 102 | node0 (job 102) | 1 | 8 | 16 | p3.8xlarge |
| 103 | node0 (job 103) | 1 | 8 | 30 | p3.8xlarge |
| 104 | node0 (job 104) | 1 | 19 | 63 | p3.16xlarge |
| 105 | node0 (job 105) | 1 | 12 | 16 | p3.16xlarge |
| 108 | node0 (job 108) | 1 | 4 | 31 | p3.2xlarge |
| 110 | node0 (job 110) | 1 | 16 | 32 | p3.8xlarge |
| 111 | node0 (job 111) | 1 | 19 | 63 | p3.16xlarge |
| 113 | node0 (job 113) | 1 | 8 | 30 | p3.16xlarge |
| 114 | node0 (job 114) | 1 | 16 | 32 | p3.8xlarge |
| 115 | node0 (job 115) | 1 | 6 | 23 | p3.8xlarge |
| 116 | node0 (job 116) | 1 | 8 | 30 | p3.8xlarge |
| 117 | node0 (job 117) | 1 | 4 | 15 | p3.2xlarge |
| 119 | node0 (job 119) | 1 | 6 | 18 | p3.8xlarge |
| 120 | node0 (job 120) | 1 | 8 | 64 | p3.8xlarge |
| 124 | node0 (job 124) | 1 | 16 | 32 | p3.8xlarge |
| 125 | node0 (job 125) | 1 | 4 | 15 | p3.2xlarge |

#### CP-SAT Optimal Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.8xlarge | 5 | node0 (job 6), node0 (job 20), node0 (job 28), node0 (job 31), node0 (job 78), node0 (job 80), node0 (job 83), node0 (job 91), node0 (job 95), node0 (job 96), node0 (job 101), node0 (job 102), node0 (job 104), node0 (job 108), node0 (job 115), node0 (job 117), node0 (job 119), node0 (job 120), node0 (job 125) |
| p3.16xlarge | 4 | node0 (job 13), node0 (job 26), node0 (job 29), node0 (job 33), node0 (job 48), node0 (job 52), node0 (job 55), node0 (job 73), node0 (job 77), node0 (job 85), node0 (job 86), node0 (job 92), node0 (job 93), node0 (job 94), node0 (job 103), node0 (job 105), node0 (job 110), node0 (job 111), node0 (job 113), node0 (job 114), node0 (job 116), node0 (job 124) |
| c7i.8xlarge | 1 | node0 (job 5) |
| r7i.2xlarge | 1 | node0 (job 40) |

---

### Snapshot t = 165600 s (46.0 h)

- **Active tasks**: 47
- **Active instances (EVA)**: 33
- **EVA $/hr**: 363.936
- **CP-SAT optimal $/hr**: 176.3772 (bound: 176.3772)
- **CP-SAT status**: OPTIMAL (solved in 0.09s)
- **Gap**: +106.34%

#### Task Set and EVA Assignment

| Task ID | Name | GPU | CPU | RAM | EVA Instance Type |
|---:|---|---:|---:|---:|---|
| 5 | node0 (job 5) | 0 | 20 | 64 | c7i.12xlarge |
| 6 | node0 (job 6) | 1 | 4 | 16 | p3.2xlarge |
| 13 | node0 (job 13) | 1 | 8 | 16 | p3.8xlarge |
| 20 | node0 (job 20) | 1 | 8 | 30 | p3.8xlarge |
| 26 | node0 (job 26) | 1 | 1 | 2 | p3.16xlarge |
| 28 | node0 (job 28) | 1 | 4 | 15 | p3.8xlarge |
| 29 | node0 (job 29) | 1 | 16 | 32 | p3.8xlarge |
| 31 | node0 (job 31) | 1 | 6 | 12 | p3.8xlarge |
| 33 | node0 (job 33) | 1 | 16 | 32 | p3.8xlarge |
| 40 | node0 (job 40) | 0 | 8 | 30 | c7i.4xlarge |
| 48 | node0 (job 48) | 1 | 12 | 46 | p3.16xlarge |
| 52 | node0 (job 52) | 1 | 16 | 32 | p3.8xlarge |
| 55 | node0 (job 55) | 1 | 19 | 63 | p3.16xlarge |
| 73 | node0 (job 73) | 1 | 16 | 57 | p3.8xlarge |
| 77 | node0 (job 77) | 1 | 8 | 30 | p3.8xlarge |
| 78 | node0 (job 78) | 1 | 19 | 63 | p3.16xlarge |
| 80 | node0 (job 80) | 1 | 4 | 15 | p3.8xlarge |
| 83 | node0 (job 83) | 1 | 8 | 30 | p3.8xlarge |
| 85 | node0 (job 85) | 1 | 8 | 30 | p3.8xlarge |
| 86 | node0 (job 86) | 1 | 12 | 32 | p3.16xlarge |
| 91 | node0 (job 91) | 1 | 4 | 15 | p3.2xlarge |
| 93 | node0 (job 93) | 1 | 8 | 30 | p3.8xlarge |
| 95 | node0 (job 95) | 1 | 4 | 24 | p3.2xlarge |
| 101 | node0 (job 101) | 1 | 19 | 63 | p3.16xlarge |
| 102 | node0 (job 102) | 1 | 8 | 16 | p3.8xlarge |
| 103 | node0 (job 103) | 1 | 8 | 30 | p3.8xlarge |
| 104 | node0 (job 104) | 1 | 19 | 63 | p3.16xlarge |
| 108 | node0 (job 108) | 1 | 4 | 31 | p3.2xlarge |
| 115 | node0 (job 115) | 1 | 6 | 23 | p3.8xlarge |
| 116 | node0 (job 116) | 1 | 8 | 30 | p3.8xlarge |
| 124 | node0 (job 124) | 1 | 16 | 32 | p3.8xlarge |
| 135 | node0 (job 135) | 1 | 19 | 63 | p3.16xlarge |
| 137 | node0 (job 137) | 1 | 12 | 46 | p3.16xlarge |
| 138 | node0 (job 138) | 1 | 12 | 46 | p3.16xlarge |
| 140 | node0 (job 140) | 1 | 4 | 15 | p3.2xlarge |
| 142 | node0 (job 142) | 1 | 8 | 30 | p3.8xlarge |
| 143 | node0 (job 143) | 1 | 8 | 30 | p3.8xlarge |
| 144 | node0 (job 144) | 1 | 4 | 30 | p3.2xlarge |
| 145 | node0 (job 145) | 1 | 8 | 32 | p3.8xlarge |
| 146 | node0 (job 146) | 1 | 4 | 15 | p3.2xlarge |
| 147 | node0 (job 147) | 1 | 12 | 46 | p3.16xlarge |
| 148 | node0 (job 148) | 1 | 16 | 32 | p3.8xlarge |
| 149 | node0 (job 149) | 1 | 16 | 32 | p3.8xlarge |
| 150 | node0 (job 150) | 1 | 19 | 63 | p3.16xlarge |
| 151 | node0 (job 151) | 1 | 4 | 30 | p3.2xlarge |
| 152 | node0 (job 152) | 1 | 12 | 46 | p3.16xlarge |
| 153 | node0 (job 153) | 1 | 8 | 30 | p3.8xlarge |

#### CP-SAT Optimal Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 1 | node0 (job 13) |
| p3.16xlarge | 7 | node0 (job 6), node0 (job 20), node0 (job 26), node0 (job 28), node0 (job 29), node0 (job 31), node0 (job 33), node0 (job 48), node0 (job 52), node0 (job 55), node0 (job 73), node0 (job 77), node0 (job 78), node0 (job 80), node0 (job 83), node0 (job 85), node0 (job 86), node0 (job 91), node0 (job 93), node0 (job 95), node0 (job 101), node0 (job 102), node0 (job 103), node0 (job 104), node0 (job 108), node0 (job 115), node0 (job 116), node0 (job 124), node0 (job 135), node0 (job 137), node0 (job 138), node0 (job 140), node0 (job 142), node0 (job 143), node0 (job 144), node0 (job 145), node0 (job 146), node0 (job 147), node0 (job 148), node0 (job 149), node0 (job 150), node0 (job 151), node0 (job 152), node0 (job 153) |
| c7i.8xlarge | 1 | node0 (job 5) |
| r7i.2xlarge | 1 | node0 (job 40) |

---

### Snapshot t = 217200 s (60.33 h)

- **Active tasks**: 40
- **Active instances (EVA)**: 25
- **EVA $/hr**: 257.856
- **CP-SAT optimal $/hr**: 129.2796 (bound: 129.2796)
- **CP-SAT status**: OPTIMAL (solved in 0.32s)
- **Gap**: +99.46%

#### Task Set and EVA Assignment

| Task ID | Name | GPU | CPU | RAM | EVA Instance Type |
|---:|---|---:|---:|---:|---|
| 26 | node0 (job 26) | 1 | 1 | 2 | p3.16xlarge |
| 28 | node0 (job 28) | 1 | 4 | 15 | p3.16xlarge |
| 29 | node0 (job 29) | 1 | 16 | 32 | p3.8xlarge |
| 31 | node0 (job 31) | 1 | 6 | 12 | p3.8xlarge |
| 33 | node0 (job 33) | 1 | 16 | 32 | p3.8xlarge |
| 40 | node0 (job 40) | 0 | 8 | 30 | c7i.4xlarge |
| 52 | node0 (job 52) | 1 | 16 | 32 | p3.8xlarge |
| 55 | node0 (job 55) | 1 | 19 | 63 | p3.16xlarge |
| 77 | node0 (job 77) | 1 | 8 | 30 | p3.16xlarge |
| 80 | node0 (job 80) | 1 | 4 | 15 | p3.16xlarge |
| 83 | node0 (job 83) | 1 | 8 | 30 | p3.16xlarge |
| 85 | node0 (job 85) | 1 | 8 | 30 | p3.16xlarge |
| 86 | node0 (job 86) | 1 | 12 | 32 | p3.16xlarge |
| 93 | node0 (job 93) | 1 | 8 | 30 | p3.8xlarge |
| 102 | node0 (job 102) | 1 | 8 | 16 | p3.8xlarge |
| 103 | node0 (job 103) | 1 | 8 | 30 | p3.8xlarge |
| 104 | node0 (job 104) | 1 | 19 | 63 | p3.16xlarge |
| 115 | node0 (job 115) | 1 | 6 | 23 | p3.8xlarge |
| 124 | node0 (job 124) | 1 | 16 | 32 | p3.8xlarge |
| 135 | node0 (job 135) | 1 | 19 | 63 | p3.16xlarge |
| 143 | node0 (job 143) | 1 | 8 | 30 | p3.8xlarge |
| 144 | node0 (job 144) | 1 | 4 | 30 | p3.8xlarge |
| 154 | node0 (job 154) | 1 | 8 | 30 | p3.8xlarge |
| 158 | node0 (job 158) | 1 | 4 | 30 | p3.2xlarge |
| 162 | node0 (job 162) | 1 | 8 | 32 | p3.8xlarge |
| 164 | node0 (job 164) | 0 | 8 | 30 | c7i.4xlarge |
| 171 | node0 (job 171) | 1 | 10 | 41 | p3.8xlarge |
| 173 | node0 (job 173) | 1 | 12 | 24 | p3.8xlarge |
| 176 | node0 (job 176) | 0 | 13 | 56 | c7i.8xlarge |
| 177 | node0 (job 177) | 1 | 4 | 6 | p3.16xlarge |
| 178 | node0 (job 178) | 1 | 8 | 30 | p3.8xlarge |
| 179 | node0 (job 179) | 0 | 13 | 56 | c7i.8xlarge |
| 181 | node0 (job 181) | 1 | 16 | 32 | p3.8xlarge |
| 183 | node0 (job 183) | 0 | 16 | 64 | c7i.8xlarge |
| 184 | node0 (job 184) | 1 | 19 | 63 | p3.16xlarge |
| 185 | node0 (job 185) | 0 | 13 | 56 | c7i.8xlarge |
| 186 | node0 (job 186) | 0 | 13 | 56 | c7i.8xlarge |
| 187 | node0 (job 187) | 0 | 13 | 56 | c7i.8xlarge |
| 188 | node0 (job 188) | 1 | 8 | 32 | p3.8xlarge |
| 189 | node0 (job 189) | 1 | 8 | 16 | p3.8xlarge |

#### CP-SAT Optimal Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.16xlarge | 5 | node0 (job 26), node0 (job 28), node0 (job 29), node0 (job 31), node0 (job 33), node0 (job 52), node0 (job 55), node0 (job 77), node0 (job 80), node0 (job 83), node0 (job 85), node0 (job 86), node0 (job 93), node0 (job 102), node0 (job 103), node0 (job 104), node0 (job 115), node0 (job 124), node0 (job 135), node0 (job 143), node0 (job 144), node0 (job 154), node0 (job 158), node0 (job 162), node0 (job 171), node0 (job 173), node0 (job 177), node0 (job 178), node0 (job 181), node0 (job 184), node0 (job 188), node0 (job 189) |
| r7i.2xlarge | 1 | node0 (job 164) |
| r7i.4xlarge | 1 | node0 (job 183) |
| r7i.8xlarge | 1 | node0 (job 176), node0 (job 179) |
| r7i.12xlarge | 1 | node0 (job 40), node0 (job 185), node0 (job 186), node0 (job 187) |

---

### Snapshot t = 258600 s (71.83 h)

- **Active tasks**: 28
- **Active instances (EVA)**: 18
- **EVA $/hr**: 187.17
- **CP-SAT optimal $/hr**: 94.446 (bound: 94.446)
- **CP-SAT status**: OPTIMAL (solved in 0.22s)
- **Gap**: +98.18%

#### Task Set and EVA Assignment

| Task ID | Name | GPU | CPU | RAM | EVA Instance Type |
|---:|---|---:|---:|---:|---|
| 26 | node0 (job 26) | 1 | 1 | 2 | p3.16xlarge |
| 28 | node0 (job 28) | 1 | 4 | 15 | p3.2xlarge |
| 31 | node0 (job 31) | 1 | 6 | 12 | p3.8xlarge |
| 33 | node0 (job 33) | 1 | 16 | 32 | p3.8xlarge |
| 40 | node0 (job 40) | 0 | 8 | 30 | c7i.4xlarge |
| 55 | node0 (job 55) | 1 | 19 | 63 | p3.16xlarge |
| 83 | node0 (job 83) | 1 | 8 | 30 | p3.8xlarge |
| 85 | node0 (job 85) | 1 | 8 | 30 | p3.8xlarge |
| 93 | node0 (job 93) | 1 | 8 | 30 | p3.8xlarge |
| 102 | node0 (job 102) | 1 | 8 | 16 | p3.8xlarge |
| 103 | node0 (job 103) | 1 | 8 | 30 | p3.8xlarge |
| 104 | node0 (job 104) | 1 | 19 | 63 | p3.16xlarge |
| 115 | node0 (job 115) | 1 | 6 | 23 | p3.8xlarge |
| 124 | node0 (job 124) | 1 | 16 | 32 | p3.8xlarge |
| 135 | node0 (job 135) | 1 | 19 | 63 | p3.16xlarge |
| 143 | node0 (job 143) | 1 | 8 | 30 | p3.8xlarge |
| 144 | node0 (job 144) | 1 | 4 | 30 | p3.2xlarge |
| 154 | node0 (job 154) | 1 | 8 | 30 | p3.8xlarge |
| 158 | node0 (job 158) | 1 | 4 | 30 | p3.2xlarge |
| 171 | node0 (job 171) | 1 | 10 | 41 | p3.8xlarge |
| 176 | node0 (job 176) | 0 | 13 | 56 | c7i.8xlarge |
| 178 | node0 (job 178) | 1 | 8 | 30 | p3.8xlarge |
| 183 | node0 (job 183) | 0 | 16 | 64 | c7i.8xlarge |
| 191 | node0 (job 191) | 1 | 12 | 46 | p3.16xlarge |
| 193 | node0 (job 193) | 1 | 12 | 46 | p3.16xlarge |
| 194 | node0 (job 194) | 1 | 12 | 46 | p3.16xlarge |
| 196 | node0 (job 196) | 1 | 1 | 2 | p3.16xlarge |
| 197 | node0 (job 197) | 1 | 8 | 16 | p3.8xlarge |

#### CP-SAT Optimal Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 6 | node0 (job 93), node0 (job 102), node0 (job 103), node0 (job 115), node0 (job 143), node0 (job 178) |
| p3.8xlarge | 2 | node0 (job 26), node0 (job 104), node0 (job 135), node0 (job 144), node0 (job 154), node0 (job 158), node0 (job 197) |
| p3.16xlarge | 2 | node0 (job 28), node0 (job 31), node0 (job 33), node0 (job 55), node0 (job 83), node0 (job 85), node0 (job 124), node0 (job 171), node0 (job 191), node0 (job 193), node0 (job 194), node0 (job 196) |
| r7i.2xlarge | 1 | node0 (job 40) |
| r7i.4xlarge | 2 | node0 (job 176), node0 (job 183) |

---

### Snapshot t = 300000 s (83.33 h)

- **Active tasks**: 20
- **Active instances (EVA)**: 11
- **EVA $/hr**: 129.234
- **CP-SAT optimal $/hr**: 64.7892 (bound: 64.7892)
- **CP-SAT status**: OPTIMAL (solved in 0.04s)
- **Gap**: +99.47%

#### Task Set and EVA Assignment

| Task ID | Name | GPU | CPU | RAM | EVA Instance Type |
|---:|---|---:|---:|---:|---|
| 26 | node0 (job 26) | 1 | 1 | 2 | p3.16xlarge |
| 28 | node0 (job 28) | 1 | 4 | 15 | p3.16xlarge |
| 33 | node0 (job 33) | 1 | 16 | 32 | p3.8xlarge |
| 40 | node0 (job 40) | 0 | 8 | 30 | c7i.4xlarge |
| 83 | node0 (job 83) | 1 | 8 | 30 | p3.16xlarge |
| 85 | node0 (job 85) | 1 | 8 | 30 | p3.8xlarge |
| 93 | node0 (job 93) | 1 | 8 | 30 | p3.8xlarge |
| 102 | node0 (job 102) | 1 | 8 | 16 | p3.8xlarge |
| 103 | node0 (job 103) | 1 | 8 | 30 | p3.8xlarge |
| 104 | node0 (job 104) | 1 | 19 | 63 | p3.16xlarge |
| 115 | node0 (job 115) | 1 | 6 | 23 | p3.8xlarge |
| 124 | node0 (job 124) | 1 | 16 | 32 | p3.8xlarge |
| 135 | node0 (job 135) | 1 | 19 | 63 | p3.16xlarge |
| 143 | node0 (job 143) | 1 | 8 | 30 | p3.8xlarge |
| 144 | node0 (job 144) | 1 | 4 | 30 | p3.2xlarge |
| 158 | node0 (job 158) | 1 | 4 | 30 | p3.2xlarge |
| 171 | node0 (job 171) | 1 | 10 | 41 | p3.8xlarge |
| 178 | node0 (job 178) | 1 | 8 | 30 | p3.8xlarge |
| 194 | node0 (job 194) | 1 | 12 | 46 | p3.16xlarge |
| 196 | node0 (job 196) | 1 | 1 | 2 | p3.16xlarge |

#### CP-SAT Optimal Assignment

| Instance Type | Count | Tasks |
|---|---:|---|
| p3.2xlarge | 1 | node0 (job 93) |
| p3.8xlarge | 5 | node0 (job 26), node0 (job 28), node0 (job 33), node0 (job 83), node0 (job 85), node0 (job 102), node0 (job 103), node0 (job 104), node0 (job 115), node0 (job 124), node0 (job 135), node0 (job 143), node0 (job 144), node0 (job 158), node0 (job 171), node0 (job 178), node0 (job 194), node0 (job 196) |
| r7i.2xlarge | 1 | node0 (job 40) |

---

## Methodology Notes

- Demand vector [GPU, CPU, RAM] taken from demand_dict in report.json.
  GPU tasks use the p3 family entry; CPU-only tasks use c7i or r7i.
- EVA cost at each snapshot = sum of $/hr for ALL provisioned instances
  (EVA pays from boot to shutdown regardless of task execution status).
- CP-SAT cost = provably optimal $/hr for the minimum-cost fleet that hosts
  the exact same concurrent task set, using any of the 21 available instance types.
- The 196-hour aggregate total vs 1-hour snapshot comparison is INVALID and excluded.
  All comparisons here are instantaneous $/hr vs instantaneous $/hr.
