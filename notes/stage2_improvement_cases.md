# Stage-2 Detailed Analysis: All Strictly Improved Cases

This document provides an in-depth, case-by-case breakdown of every real scheduling decision point in the 105-decision Stage-2 experiment where CP-SAT refinement strictly improved Eva's planned configuration.

Across the 105 sampled decisions from `pai_trace/traces/pai_200.json`, exactly **3 decisions** achieved strict cost improvement over Eva. All 3 cases were solved to **mathematical optimality** (`OPTIMAL`) within the strict 5.0-second time budget.

---

## Case 1: Decision #2 (Simulation Time $t = 4200\,\text{s}$)

### 1. State Summary
- **Simulation Time**: $t = 4200.0\,\text{s}$
- **Reconfiguration Mode**: `LOCAL`
- **Candidate Tasks**: 4 tasks (`[0, 1, 2, 3]`)
- **Existing Active Instances**: 2 instances (`Instance 2`, `Instance 3`)
- **Combinatorial Flexibility**: 8 feasible (task, instance) assignment pairs (Flexibility Ratio = 2.00)
- **Horizon $T$**: $3184.07\,\text{s}$ ($0.884\,\text{hr}$)

### 2. Configuration Comparison
- **Original Eva Placement**:
  - `Instance 2`: `[0, 1, 2]` (3 tasks co-located)
  - `Instance 3`: `[3]` (1 task solitary)
- **CP-SAT Refined Placement**:
  - `Instance 2`: `[0, 2]` (2 tasks co-located)
  - `Instance 3`: `[1, 3]` (2 tasks co-located)

### 3. Physical Mechanism & Contention Analysis
- **Initial Placement**: Tasks 0, 1, and 2 were co-located on Instance 2. Under Eva's contention model, a 3-way co-location degrades task throughput by $0.95^2 = 0.9025$ ($9.75\%$ degradation).
- **CP-SAT Action**: CP-SAT recognized that Instance 3 was underutilized (holding only Task 3). By migrating Task 1 from Instance 2 to Instance 3, both instances host exactly two tasks.
- Under 2-way co-location, throughput factor improves to $0.95^1 = 0.9500$ (only $5.0\%$ degradation).

### 4. Mathematical Objective Breakdown
| Component | Original Eva Plan | CP-SAT Refined Plan | Delta |
| :--- | :---: | :---: | :---: |
| **Provisioning Saving Rate** | $0.00131400\,\$/\text{s}$ | $0.00272000\,\$/\text{s}$ | **+$0.00140600\,\$/\text{s}$** (+107.0%) |
| **Rate Gain over Horizon $T$** | — | — | **+$4.4768** |
| **Migration Cost** | $\$0.0000$ | $\$0.5848$ | **+$0.5848$** (Task 1 migrated) |
| **Net Saving ($)** | **$4.1839** | **$8.0759** | **+$3.8920** |
| **Relative Improvement (%)** | — | — | **+93.02%** |

### 5. Solver Performance
- **Solver Status**: `OPTIMAL`
- **CP-SAT Solver Wall Time**: **$0.017\,\text{s}$**
- **Preprocessing Time**: **$0.017\,\text{s}$**
- **Total Refinement Wall Time**: **$0.035\,\text{s}$**
- **Optimality Gap**: **$0.00\%$**

---

## Case 2: Decision #3 (Simulation Time $t = 9600\,\text{s}$)

### 1. State Summary
- **Simulation Time**: $t = 9600.0\,\text{s}$
- **Reconfiguration Mode**: `LOCAL`
- **Candidate Tasks**: 7 tasks (`[0, 1, 3, 4, 5, 6, 7]`)
- **Existing Active Instances**: 4 instances (`Instance 3`, `Instance 4`, `Instance 5`, `Instance 6`)
- **Combinatorial Flexibility**: 19 feasible assignment pairs (Flexibility Ratio = 2.71)
- **Horizon $T$**: $9115.28\,\text{s}$ ($2.532\,\text{hr}$)

### 2. Configuration Comparison
- **Original Eva Placement**:
  - `Instance 3`: `[1, 3, 6]` (3 tasks co-located)
  - `Instance 4`: `[0]` (1 task solitary)
  - `Instance 5`: `[4]` (1 task solitary)
  - `Instance 6`: `[5]` (1 task solitary)
  - `New Instance (-32, 1)`: `[7]` (1 task solitary)
- **CP-SAT Refined Placement**:
  - `Instance 3`: `[1, 3]` (2 tasks co-located)
  - `Instance 4`: `[0]` (1 task solitary)
  - `Instance 5`: `[4]` (1 task solitary)
  - `Instance 6`: `[5]` (1 task solitary)
  - `New Instance (-500, 1)`: `[6, 7]` (2 tasks co-located)

### 3. Physical Mechanism & Contention Analysis
- **Eva Suboptimality**: Eva launched a new instance `(-32, 1)` for new task 7, while leaving Instance 3 heavily congested with 3 co-located tasks `[1, 3, 6]`.
- **CP-SAT Action**: CP-SAT relocated Task 6 off Instance 3 and co-located it with Task 7 on the newly provisioned instance `(-500, 1)`.
- This broke the 3-way contention bottleneck on Instance 3 without overloading any other existing machine.

### 4. Mathematical Objective Breakdown
| Component | Original Eva Plan | CP-SAT Refined Plan | Delta |
| :--- | :---: | :---: | :---: |
| **Provisioning Saving Rate** | $0.00306136\,\$/\text{s}$ | $0.00328326\,\$/\text{s}$ | **+$0.00022190\,\$/\text{s}$** (+7.25%) |
| **Rate Gain over Horizon $T$** | — | — | **+$2.0227** |
| **Migration Cost** | $\$1.2920$ | $\$1.3133$ | **+$0.0213$** |
| **Net Saving ($)** | **$26.6132** | **$28.6145** | **+$2.0014** |
| **Relative Improvement (%)** | — | — | **+7.52%** |

### 5. Solver Performance
- **Solver Status**: `OPTIMAL`
- **CP-SAT Solver Wall Time**: **$0.061\,\text{s}$**
- **Preprocessing Time**: **$0.041\,\text{s}$**
- **Total Refinement Wall Time**: **$0.103\,\text{s}$**
- **Optimality Gap**: **$0.00\%$**

---

## Case 3: Decision #4 (Simulation Time $t = 11100\,\text{s}$)

### 1. State Summary
- **Simulation Time**: $t = 11100.0\,\text{s}$
- **Reconfiguration Mode**: `GLOBAL`
- **Candidate Tasks**: 11 tasks (`[0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 11]`)
- **Existing Active Instances**: 4 instances (`Instance 6`, `Instance 8`, `Instance 9`, `Instance 11`)
- **Combinatorial Flexibility**: 34 feasible assignment pairs (Flexibility Ratio = 3.09)
- **Horizon $T$**: $2292.93\,\text{s}$ ($0.637\,\text{hr}$)

### 2. Configuration Comparison
- **Original Eva Placement**:
  - `Instance 6`: `[5]` (1 task)
  - `Instance 8`: `[0, 4, 11]` (3 tasks co-located)
  - `Instance 9`: `[3, 7, 8]` (3 tasks co-located)
  - `Instance 11`: `[6, 9, 10]` (3 tasks co-located)
  - `New Instance (-46, 1)`: `[1]` (1 task solitary)
- **CP-SAT Refined Placement**:
  - `Instance 6`: `[5]` (1 task)
  - `Instance 8`: `[0, 1, 4]` (3 tasks co-located)
  - `Instance 9`: `[7, 8]` (2 tasks co-located)
  - `Instance 11`: `[6, 9, 10]` (3 tasks co-located)
  - `New Instance (-500, 1)`: `[3, 11]` (2 tasks co-located)

### 3. Physical Mechanism & Contention Analysis
- **Eva Suboptimality**: Eva created three separate 3-way co-locations (`Instance 8`, `Instance 9`, `Instance 11`), while provisioning an entirely new instance for solitary task 1.
- **CP-SAT Action**: CP-SAT orchestrated a global swap:
  1. Task 1 was placed on Instance 8 instead of being solitary.
  2. Task 11 was migrated off Instance 8 to the new instance `(-500, 1)`.
  3. Task 3 was migrated off Instance 9 to pair with Task 11 on the new instance `(-500, 1)`.
- This reduced `Instance 9` from 3 tasks to 2 tasks (`[7, 8]`), while utilizing the new instance effectively (`[3, 11]`), cutting interference across the cluster.
- Crucially, the total migration cost of CP-SAT was **identical** to Eva ($2.1488 in both plans), meaning all rate gains translated directly to net saving.

### 4. Mathematical Objective Breakdown
| Component | Original Eva Plan | CP-SAT Refined Plan | Delta |
| :--- | :---: | :---: | :---: |
| **Provisioning Saving Rate** | $0.00440451\,\$/\text{s}$ | $0.00471901\,\$/\text{s}$ | **+$0.00031450\,\$/\text{s}$** (+7.14%) |
| **Rate Gain over Horizon $T$** | — | — | **+$0.7211** |
| **Migration Cost** | $\$2.1488$ | $\$2.1488$ | **$0.0000** |
| **Net Saving ($)** | **$7.9504** | **$8.6716** | **+$0.7211** |
| **Relative Improvement (%)** | — | — | **+9.07%** |

### 5. Solver Performance
- **Solver Status**: `OPTIMAL`
- **CP-SAT Solver Wall Time**: **$2.404\,\text{s}$**
- **Preprocessing Time**: **$0.101\,\text{s}$**
- **Total Refinement Wall Time**: **$2.506\,\text{s}$**
- **Optimality Gap**: **$0.00\%$**

---

## Synthesis of Common Conditions

Across all 3 cases:
1. **Identical Structural Flaw in Eva**: Eva stacked 3 tasks on an instance while another instance hosted a single solitary task. Eva's greedy logic sorts candidate slots by cost efficiency but does not re-evaluate intra-cluster load balancing once an instance is selected.
2. **Quadratic Penalty Disadvantage**: Because contention penalties scale quadratically with co-located pairs, splitting a 3-task cluster ($3$ pairs) into two 2-task clusters ($1 + 1 = 2$ pairs) eliminates $33\%$ of the interference overhead.
3. **Horizon Sufficiency**: All three decisions occurred with $T > 2000\,\text{s}$, giving enough continuous run-time for throughput gains to decisively beat one-off migration costs.
4. **Computational Feasibility**: All 3 cases were solved to proven global optimality within 2.5 seconds ($0.017\,\text{s}$, $0.061\,\text{s}$, $2.404\,\text{s}$).
