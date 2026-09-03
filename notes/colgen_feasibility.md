# Column Generation Feasibility Note: TNRP-Penalized Task Packing

**Document Target**: `notes/colgen_feasibility.md`  
**Date**: September 2026  
**Problem**: Snapshot decision-point scheduling of heterogeneous GPU/CPU tasks onto EC2 instance types with TNRP interference penalties.

---

## 1. Executive Summary

This note assesses the mathematical and algorithmic feasibility of applying **Dantzig-Wolfe Decomposition / Column Generation (Branch-and-Price)** to the snapshot packing problem with TNRP contention penalties.

- **Master Problem Structure**: Set Partitioning / Set Covering over valid single-instance packing configurations (patterns).
- **Pricing Subproblem Structure**: Multi-dimensional Quadratic / Nonlinear Knapsack Problem (MCQP) per instance type.
- **Key Assessment**: 
  - An exact **Branch-and-Price** solver would require **40–60 engineering hours** (1.5–2 weeks of focused implementation).
  - A simplified **Price-and-Branch heuristic** (column generation at the root node followed by integer master solve) would take **12–16 engineering hours**.
  - **Verdict**: Given that native **CP-SAT** and **SCIP** already solve 5/8 snapshots to provable optimality in $\le 60$ seconds and yield tight bounds on the rest, a full custom Column Generation solver is **not recommended** for the current project scope unless snapshot sizes scale to $N \gg 200$ tasks.

---

## 2. Mathematical Formulation

### 2.1 Pattern Representation
Let $\mathcal{T}$ be the set of 21 EC2 instance types (costs $C_t$, resource capacities $\mathbf{cap}_t = (\text{gpu}_t, \text{cpu}_t, \text{mem}_t)$).  
Let $\mathcal{I} = \{1, \dots, N\}$ be the tasks in a snapshot (demands $\mathbf{d}_i$).

A **pattern** (column) $p = (t, S)$ represents a valid single-instance assignment:
- $t \in \mathcal{T}$: instance type.
- $S \subseteq \mathcal{I}$: subset of tasks packed onto this single instance.
- **Feasibility condition**:
  $$\sum_{i \in S} \mathbf{d}_i \le \mathbf{cap}_t \quad (\text{component-wise for GPU, CPU, RAM})$$
- **Pattern Cost $c_p$**:
  $$c_p = C_t + \text{TNRP}(t, S)$$
  where $\text{TNRP}(t, S)$ is the throughput degradation penalty.

> **Crucial Advantage of Pattern Formulation**: Because $S$ is explicit in pattern $p$, the TNRP cost does **not** need to be approximated or linearized. Tuple-dependent lookups from EVA's `contention_map` can be computed directly and exactly during column generation.

---

### 2.2 Restricted Master Problem (RMP)

Let $\Omega$ be the current pool of generated feasible patterns. Let $a_{ip} = 1$ if task $i \in S_p$, and 0 otherwise.

**Primal RMP (Linear Relaxation)**:
$$\min \sum_{p \in \Omega} c_p \lambda_p$$
$$\text{subject to:}$$
$$\sum_{p \in \Omega} a_{ip} \lambda_p \ge 1 \quad \forall i \in \mathcal{I} \quad (\text{Dual: } \pi_i \ge 0)$$
$$\lambda_p \ge 0 \quad \forall p \in \Omega$$

*(Covering formulation $\ge 1$ is mathematically equivalent to partitioning $= 1$ because costs $c_p$ and penalties are positive and monotone).*

---

### 2.3 Pricing Subproblem

For a given dual vector $\boldsymbol{\pi} = (\pi_1, \dots, \pi_N)$, the reduced cost of pattern $p = (t, S)$ is:
$$\bar{c}_p = c_p - \sum_{i \in S} \pi_i = C_t + \text{TNRP}(t, S) - \sum_{i \in S} \pi_i$$

A column with negative reduced cost ($\bar{c}_p < 0$) can enter the basis to decrease total cost. The pricing subproblem decomposes by instance type $t \in \mathcal{T}$:

$$\text{For each } t \in \mathcal{T}: \quad \min_{z \in \{0,1\}^N} \left[ C_t + \text{TNRP}(t, z) - \sum_{i=1}^N \pi_i z_i \right]$$
$$\text{s.t.} \quad \sum_{i=1}^N \mathbf{d}_i z_i \le \mathbf{cap}_t$$

#### Subproblem Complexity Analysis:
1. **CPU-only Instance Types** ($P_{ij} = 0$):
   - Here $\text{TNRP}(t, z) = 0$.
   - The pricing subproblem is a standard **Multi-dimensional 0-1 Knapsack Problem** (MKP). Easily solved via integer programming or DP branch-and-bound.
2. **GPU Instance Types** ($P_{ij} > 0$):
   - With pairwise TNRP: $\text{TNRP}(t, z) = \sum_{i < j} P_{ij} z_i z_j$. This is a **Binary Quadratic Knapsack Problem** with 3 resource constraints.
   - With arbitrary tuple-dependent contention: The objective is non-linear and non-separable.
   - **Saving Grace**: Physical capacity limits the number of GPU tasks on any single instance:
     - $p3.2xlarge$ (1 GPU): at most 1 GPU task ($|S_{gpu}| \le 1$).
     - $p3.8xlarge$ (4 GPUs): at most 4 GPU tasks ($|S_{gpu}| \le 4$).
     - $p3.16xlarge$ (8 GPUs): at most 8 GPU tasks ($|S_{gpu}| \le 8$).
   - Because $|S_{gpu}| \le 8$, the interaction graph on any single instance is tiny. The pricing subproblem can be solved either by:
     - A small internal CP-SAT or SCIP instance ($\le 0.01$s per instance type).
     - Filtered branch-and-bound enumeration over cliques of compatible tasks.

---

## 3. Branch-and-Price Architecture & Technical Challenges

To obtain an exact integer solution $\lambda_p \in \{0, 1\}$, standard branch-and-bound cannot simply branch on $\lambda_p$ (doing so sets $\lambda_p = 0$, which requires forbidding pattern $p$ in the pricing subproblem, destroying its structure).

Instead, a full implementation requires:
1. **Ryan-Foster Branching**:
   - Branch on pairs of tasks $(i, j)$:
     - **Branch 1**: Tasks $i$ and $j$ *must* be together ($z_i = z_j$, contract nodes into a single composite task).
     - **Branch 2**: Tasks $i$ and $j$ *cannot* be together ($z_i + z_j \le 1$, add edge constraint to pricing).
2. **Dual Degeneracy and Oscillation**:
   - Set covering master problems exhibit severe dual degeneracy. Dual variables $\pi_i$ oscillate wildly between extreme values (e.g., 0 and $C_t$), leading to poor column generation convergence ("tailing-off" effect).
   - Stabilization techniques (Kelley cutting planes, box penalties, or Wentges smoothing) are required.
3. **Master Problem Solver**:
   - Requires an LP solver (e.g., `scipy.optimize.linprog(method='highs')`, PySCIPOpt LP, or PuLP).

---

## 4. Implementation Effort Breakdown (Honest Hours)

| Component | Task Description | Estimated Hours |
|---|---|:---:|
| **1. Restricted Master LP** | Setup Highs/PuLP LP model, dual variable extraction, initial basis with dummy columns | 4 – 6 h |
| **2. Pricing Engine** | Implement 21 subproblems (CPU knapsack + GPU quadratic/enumerative knapsack with exact TNRP) | 8 – 10 h |
| **3. Column Generation Loop** | Iterative column injection, reduced cost stopping criterion ($\bar{c} \ge -\epsilon$), pool management | 4 – 6 h |
| **4. Dual Stabilization** | Box stabilization / smoothing to prevent tailing-off and slow convergence | 6 – 8 h |
| **5. Ryan-Foster Branching** | Node branching logic, pricing constraint inheritance, search tree management | 12 – 16 h |
| **6. Integration & Testing** | Benchmarking across 8 snapshots, gap calculation vs CP-SAT, edge-case debugging | 6 – 10 h |
| **Total Effort** | **Full Branch-and-Price Exact Solver** | **40 – 56 h** |

### Alternative: "Price-and-Branch" Heuristic (Root Node Only)
If we only perform column generation at the root node to populate $\Omega$, and then solve the resulting Master as an Integer Program (IP) once:
- Eliminates Ryan-Foster branching tree (Components 5 & partially 4).
- **Estimated Effort**: **12 – 16 hours** (2 focused days).
- **Risk**: Root-node patterns alone may not contain the integer optimal combination, leaving a residual gap.

---

## 5. Feasibility Verdict & Recommendation

1. **Is it mathematically feasible?**
   **Yes**. The small cardinality of GPU tasks per physical instance ($|S| \le 8$) makes the pricing subproblem tractable despite the non-linear contention function.

2. **Is it computationally advantageous over CP-SAT / SCIP?**
   **No, not at current problem scale ($N \le 47$)**.
   - CP-SAT and SCIP already solve $N \approx 30$ in $< 1$ second and $N = 47$ in 60 seconds.
   - Column generation shines when $N \in [200, 2000]$, where compact MIPs run out of memory. For $N \le 47$, the overhead of LP-simplex re-solves, dual oscillation, and pricing calls often exceeds CP-SAT's propagation speed.

3. **Recommendation**:
   **Do not proceed with full Branch-and-Price implementation.**  
   The project already possesses:
   - Exact, proven global optima via CP-SAT and SCIP (MILP).
   - High-speed metaheuristics (GA / SA) for millisecond-scale scheduling.
   Column generation would absorb 40–50+ hours of development without offering superior cost solutions over the already optimal results.
