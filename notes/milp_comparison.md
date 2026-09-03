# EVA vs CP-SAT vs MILP (SCIP): Decision-Point Snapshot Comparison

This report compares the TNRP-corrected CP-SAT model to an identical MILP formulation solved via PySCIPOpt (since Gurobi was not licensed).

| Timestamp (s) | Tasks (GPU/CPU) | EVA $/hr | **CP-SAT TNRP $/hr** | **CP-SAT Gap %** | **MILP TNRP $/hr** | **MILP Gap %** | Solver |
|---:|---:|---:|---:|---:|---:|---:|---|
| 9900 | 8 (7/1) | 103.1220 | **45.2023** | **+128.13%** | **45.2023** | **+0.00%** | SCIP |
| 51300 | 30 (26/4) | 212.3640 | **179.4556** | **+18.34%** | **179.4556** | **+0.00%** | SCIP |
| 93000 | 31 (28/3) | 223.1760 | **175.3580** | **+27.27%** | **175.3580** | **+0.00%** | SCIP |
| 134400 | 43 (41/2) | 327.2160 | **295.1880** | **+10.85%** | **295.3471** | **+17.52%** | SCIP |
| 165600 | 47 (45/2) | 363.9360 | **340.0843** | **+7.01%** | **360.2342** | **+26.96%** | SCIP |
| 217200 | 40 (32/8) | 257.8560 | **221.8907** | **+16.21%** | **219.8405** | **+11.22%** | SCIP |
| 258600 | 28 (25/3) | 187.1700 | **140.2726** | **+33.43%** | **140.2726** | **+0.00%** | SCIP |
| 300000 | 20 (19/1) | 129.2340 | **93.9173** | **+37.60%** | **93.9173** | **+0.00%** | SCIP |

## Summary
- CP-SAT reached OPTIMAL on 3 snapshots.
- MILP (SCIP) reached OPTIMAL on 5 snapshots.
