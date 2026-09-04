# First Real-Data Validation of Eva-Guided CP-SAT Refinement

**Experiment:** Replay of the real scheduling decision at $t=3000$ from the reproduced original Eva `pai_200` benchmark run.  
**Mode:** Single-decision runtime interception and CP-SAT refinement replay.  
**Diagnostic File:** `notes/first_real_cpsat_refinement.md`  
**Execution Timestamp:** 2026-09-04 12:14:12

---

## Executive Summary

At simulation timestamp $t=3000$, Eva performs its first **global reconfiguration**. We intercepted the live simulator runtime state and passed the identical state to both Eva's `EVAGangScheduler` and the `refine_with_cpsat` solver under exact, un-tuned TNRP-corrected semantics.

### Outcome
```
NO IMPROVEMENT FOUND
```
* **CP-SAT Solver Status:** `OPTIMAL` (solved in $1.083\,\text{s}$).
* **Eva Net Saving:** $\$4.1905$ (over horizon $T = 3000\,\text{s}$).
* **CP-SAT Net Saving:** $\$4.1905$ (identical).
* **Objective Improvement:** $\$0.0000$.
* **Plan Selected:** `EVA` (baseline plan preserved).

**Scientific Finding:** At $t=3000$, Eva's heuristic decision—migrating the 2 existing running tasks off their individual `p3.8xlarge` instances and co-locating them with newly arrived Task 2 onto a single new `p3.16xlarge` instance—is **provably globally optimal**. CP-SAT independently converged to the exact same configuration and proved global optimality with 0 gap, verifying that Eva's heuristic did not leave any cost on the table at this decision point. In accordance with the research contract, the refiner made no modification and returned Eva's plan unchanged.

---

## Complete 20-Point Audit

### 1. Simulation Timestamp
* $t = 3000\,\text{seconds}$ ($50.0\,\text{minutes}$ into the simulation).

### 2. Current Configuration (`current_config`)
Prior to the scheduling decision at $t=3000$, two instances were actively running:
* **Instance `0`** (`p3.8xlarge`): Running Task `0` (Job `0`, `resnet18[0]`).
* **Instance `1`** (`p3.8xlarge`): Running Task `1` (Job `1`, `sage[0]`).
```json
{
  "0": [0],
  "1": [1]
}
```

### 3. Reconfigurable Tasks
All 3 tasks across all 3 unfinished jobs were reconfigurable:
1. **Task `0` (Job `0`, `resnet18[0]`):**
   * Demands: `[1 GPU, 12 CPU, 16 GB RAM]` (family `p3`).
   * Minimum standalone instance type: `p3.8xlarge` ($\$12.24/\text{hr}$).
   * Status: Currently executing on Instance `0`.
2. **Task `1` (Job `1`, `sage[0]`):**
   * Demands: `[1 GPU, 6 CPU, 12 GB RAM]` (family `p3`).
   * Minimum standalone instance type: `p3.8xlarge` ($\$12.24/\text{hr}$).
   * Status: Currently executing on Instance `1`.
3. **Task `2` (Job `2`, `gcn[0]`):**
   * Demands: `[1 GPU, 12 CPU, 24 GB RAM]` (family `p3`).
   * Minimum standalone instance type: `p3.8xlarge` ($\$12.24/\text{hr}$).
   * Status: Newly arrived at $t=2850$, in queue awaiting placement.

### 4. Fixed Tasks
* None (`{}`). All unfinished tasks participated in the reconfiguration.

### 5. Available Existing Instances
* **Instance `0`**: Type `p3.8xlarge` (id: 1, family: `p3`), committed tasks: `[0]`.
* **Instance `1`**: Type `p3.8xlarge` (id: 1, family: `p3`), committed tasks: `[1]`.

### 6. Instance Types and Capacities
The cluster catalog contains 21 virtual EC2 types across 3 families (`p3`, `c7i`, `r7i`). Key GPU types relevant to this decision:
* **`p3.2xlarge`** (id 0): Capacity `[1 GPU, 4 CPU, 61 GB RAM]`, Cost: $\$3.06/\text{hr}$.
  *(Note: Cannot host Task 0 or Task 2 because each demands 12 vCPUs > 4 vCPUs capacity)*.
* **`p3.8xlarge`** (id 1): Capacity `[4 GPU, 16 CPU, 244 GB RAM]`, Cost: $\$12.24/\text{hr}$.
* **`p3.16xlarge`** (id 2): Capacity `[8 GPU, 32 CPU, 488 GB RAM]`, Cost: $\$24.48/\text{hr}$.

### 7. Instance Costs
* `p3.2xlarge`: $\$3.06/\text{hr}$ ($\$0.000850/\text{s}$).
* `p3.8xlarge`: $\$12.24/\text{hr}$ ($\$0.003400/\text{s}$).
* `p3.16xlarge`: $\$24.48/\text{hr}$ ($\$0.006800/\text{s}$).

### 8. Contention Information
Contention rates evaluated between all pairs of reconfigurable tasks:
* `resnet18[0]_node0` $\leftrightarrow$ `sage[0]_node0`: $\text{rate}(i \mid j) = 0.95$, $\text{rate}(j \mid i) = 0.95$.
* `resnet18[0]_node0` $\leftrightarrow$ `gcn[0]_node0`: $\text{rate}(i \mid j) = 0.95$, $\text{rate}(j \mid i) = 0.95$.
* `sage[0]_node0` $\leftrightarrow$ `gcn[0]_node0`: $\text{rate}(i \mid j) = 0.95$, $\text{rate}(j \mid i) = 0.95$.

Pairwise TNRP interference penalties:
* For each co-located pair on a multi-GPU instance, each task suffers a $5\%$ slowdown against its minimum standalone cost ($\$12.24/\text{hr}$):
  $$\text{penalty}(i, j) = 12.24 \times (1 - 0.95) + 12.24 \times (1 - 0.95) = \$1.224/\text{hr}$$

### 9. Migration Costs
Evaluated using Eva's job migration and startup penalty functions:
* **Per-job migration cost:**
  * Job `0` (`resnet18[0]`): $\$0.3094$.
  * Job `1` (`sage[0]`): $\$0.5814$.
  * Job `2` (`gcn[0]`): $\$0.0952$.
* **New-instance startup penalty:**
  * Eva charges $300\,\text{seconds}$ of hourly cost for launching a fresh instance:
    $$\text{startup}(\text{p3.16xlarge}) = \frac{\$24.48}{3600} \times 300 = \$2.0400$$
* **Total Migration Cost for Global Consolidation:**
  $$\text{mig\_cost} = \text{mig}(\text{Job } 0) + \text{mig}(\text{Job } 1) + \text{startup}(\text{p3.16xlarge}) = 0.3094 + 0.5814 + 2.0400 = \$3.0260$$
  *(Note: Job 2 is newly arriving, so it incurs no migration cost)*.

### 10. Eva Planned Config (`eva_planned_config`)
```json
{
  "(-10, 2)": [2, 0, 1]
}
```
Eva provisions a single new `p3.16xlarge` (type id 2, pseudo id -10), co-locates all 3 tasks `[0, 1, 2]`, and terminates instances `0` and `1`.

### 11. Eva Objective / Net Saving
* **Reconfiguration Horizon ($T$):** $3000\,\text{seconds}$ ($0.8333\,\text{hours}$).
* **Provision Saving per Second:**
  * Standalone Opportunity Cost: $(12.24 + 12.24 + 12.24) / 3600 = \$0.010200/\text{s}$.
  * Effective Opportunity Cost after 3-way contention ($0.95^2 = 0.9025$ factor):
    $$\text{opp\_cost\_per\_sec} = 3 \times \frac{12.24 \times 0.9025}{3600} = \$0.0092055/\text{s}$$
  * Actual Instance Cost: $\$24.48 / 3600 = \$0.0068000/\text{s}$.
  * Provision Saving per Second: $0.0092055 - 0.0068000 = \$0.0024055/\text{s}$.
* **Eva Net Saving Over Horizon $T$:**
  $$\text{net\_saving} = 0.0024055 \times 3000 - 3.0260 = \$4.1905$$

### 12. CP-SAT Refined Planned Config
```json
{
  "(-10, 2)": [2, 0, 1]
}
```
CP-SAT converged to the identical configuration.

### 13. CP-SAT Objective / Net Saving
* **CP-SAT Provision Saving per Second:** $\$0.0024055/\text{s}$.
* **CP-SAT Migration Cost:** $\$3.0260$.
* **CP-SAT Net Saving:** $\$4.1905$.

### 14. Objective Improvement
$$\Delta \text{Objective} = \$4.1905 - \$4.1905 = \$0.0000$$

### 15. Migration Cost Difference
$$\Delta \text{Migration} = \$3.0260 - \$3.0260 = \$0.0000$$

### 16. Provisioning Cost Difference
$$\Delta \text{Provisioning} = \$0.0000$$

### 17. Solver Status
* `OPTIMAL` (proved global optimality).

### 18. Best Bound
* Objective bound: `-26390792.0` (scaled micro-dollar equivalent, matched incumbent).

### 19. Solver Wall Time
* `1.083 seconds` (well within the $5.0\,\text{s}$ limit).

### 20. Final Selection
* `EVA` (selected baseline plan due to zero delta).

---

## Validation Requirements Checklist

| Requirement | Description | Result | Details |
| :---: | :--- | :---: | :--- |
| **A** | Verify Eva's original plan is feasible | **PASS** | `_check_config_feasibility()` passed with 0 errors. |
| **B** | Verify CP-SAT's returned plan is feasible | **PASS** | `_check_config_feasibility()` passed with 0 errors. |
| **C** | Verify every reconfigurable task is assigned exactly once | **PASS** | Tasks `0, 1, 2` appear once each on instance `(-10, 2)`. |
| **D** | Verify fixed tasks remain fixed | **PASS** | No fixed tasks were present or displaced. |
| **E** | Verify family compatibility | **PASS** | All tasks require family `p3`; placed on instance type `p3.16xlarge`. |
| **F** | Verify GPU/CPU/RAM capacities | **PASS** | Demand: `[3 GPU, 30 CPU, 52 GB RAM]`; Capacity: `[8 GPU, 32 CPU, 488 GB RAM]`. Usage: $37.5\%$ GPU, $93.75\%$ CPU, $10.7\%$ RAM. |
| **G** | Verify plan is accepted by `_simulate_reconfigure()` path | **PASS** | Validated via dry-run of key transformations in master actuation layer. |
| **H** | Verify claimed improvement is from actual modelled values | **PASS** | Verified $\Delta = 0.0000$; no artificial adjustments applied. |

---

## Placement & Provisioning Analysis

Why is this decision point significant?
1. **Trade-off between Local and Global Reconfiguration:**
   * If Eva had kept Instance `0` and Instance `1` and merely launched a new instance for Task `2` (local reconfiguration), it would have spent $\$12.24 + \$12.24 + \$12.24 = \$36.72/\text{hr}$ across 3 instances with a migration cost of $\$1.1152$, resulting in a net saving of $-\$1.12$.
   * By migrating Tasks `0` and `1` onto a single `p3.16xlarge` ($\$24.48/\text{hr}$), the cluster saves $\$12.24/\text{hr}$ in hardware costs ($0.0034/\text{s}$). Even after paying $3$-way interference ($0.0010/\text{s}$) and the $\$3.026$ migration + startup penalty, the net saving over $3000\,\text{s}$ is $+\$4.19$.
2. **CP-SAT Confirms Global Optimality:**
   * Why couldn't CP-SAT pack them onto a `p3.8xlarge`?
     Total CPU demand is $12 + 6 + 12 = 30$ vCPUs. A `p3.8xlarge` only has 16 vCPUs. Therefore, a `p3.8xlarge` is physically infeasible for all 3 tasks.
   * Could CP-SAT pack Tasks `0` and `1` on one `p3.8xlarge` (demanding 18 vCPUs > 16 vCPUs)? No, still infeasible.
   * Could Tasks `1` and `2` share a `p3.8xlarge` ($6 + 12 = 18 > 16$)? No, infeasible.
   * Hence, the minimum cost allocation capable of packing all 3 tasks together is indeed `p3.16xlarge`.
   * The CP-SAT solver proved within $1.083\,\text{s}$ that no alternative placement across any of the 21 available instance types yields higher net savings.
3. **Refinement Safety Protocol in Action:**
   * Because CP-SAT identified the exact same optimal value, it did not replace the plan. The fallback contract held cleanly, logging zero regressions and preserving Eva's native actuation.
