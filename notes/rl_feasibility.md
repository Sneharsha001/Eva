# Reinforcement Learning Scoping Note: Learning-Based Cloud Scheduling with TNRP

**Document Target**: `notes/rl_feasibility.md`  
**Date**: September 2026  
**Status**: Scoping & Feasibility Only (Not Recommended for Current Scope)

---

## 1. Executive Summary

This note evaluates the feasibility, architectural requirements, and realistic development timeline of applying **Deep Reinforcement Learning (DRL)** to the cloud task scheduling problem modeled in EVA (heterogeneous GPU/CPU task placement with TNRP contention penalties).

- **Core Finding**: Implementing an RL agent that reliably and generalizably outperforms EVA's existing gang-scheduling heuristic would require **6 to 9 weeks** of dedicated machine learning engineering, given the total absence of RL training infrastructure in this codebase.
- **Data Reality**: The existing single trace (`pai_200`) and 8 decision snapshots are **entirely insufficient** for RL training. Training on a single trace produces catastrophic memorization without out-of-sample generalization.
- **Recommendation for Paper**: Frame Deep Reinforcement Learning as **Future Work**. Position the paper's current contributions as establishing:
  1. The **exact offline ceiling and bounds** via CP-SAT and SCIP (MILP).
  2. The **fast heuristic frontier** via Genetic Algorithms and Simulated Annealing.
  3. The evaluation of EVA's online heuristic against these formal bounds.

---

## 2. MDP Formulation: State, Action, and Reward

Formulating cloud task placement as a Markov Decision Process (MDP) reveals several non-trivial architectural complexities:

### 2.1 State Space ($\mathcal{S}$)
A naive flat feature vector cannot represent this problem because the number of active instances $M(t)$ and queue size $K(t)$ vary dynamically. The state must be permutation-invariant and variable-length:

1. **Active Instance States**:
   - For each active instance $m \in \{1, \dots, M(t)\}$:
     - Instance type features: cost $/hr, GPU capacity, vCPU capacity, Memory capacity.
     - Current utilization: remaining GPU, vCPU, RAM.
     - Task occupancy: set of task labels currently running (needed to calculate contention rates).
     - Remaining lease time: fraction of current billable hour elapsed.
2. **Pending Task Queue**:
   - For each queued task $k \in \{1, \dots, K(t)\}$:
     - Demands: (GPU, vCPU, RAM), estimated runtime.
     - Task identity / label (for contention lookup).
     - Job gang affinity: whether it must be co-scheduled with other tasks in the same job.
3. **Representation Architecture**:
   - Requires a **Heterogeneous Graph Neural Network (GNN)** (e.g., Decima-style bipartite graph between task nodes and instance nodes) or a **Transformer / Pointer Network** with cross-attention.

### 2.2 Action Space ($\mathcal{A}$)
At each decision step (e.g., placing the head of the queue):
- **Option 1**: Place task on existing active instance $m \in \{1, \dots, M(t)\}$ (requires dynamic action masking based on multi-dimensional capacity constraints).
- **Option 2**: Spin up a new instance of type $t \in \{1, \dots, 21\}$.
- **Option 3**: Defer / leave task in queue (wait action).
- **Action space dimensionality**: $|A(t)| = M(t) + 21 + 1$ (dynamically resizing action space with invalid action masking).

### 2.3 Reward Function ($\mathcal{R}$)
The reward must reflect the trade-off between monetary provisioning cost, TNRP interference penalty, and queuing latency:
$$R_t = - \left( \alpha \cdot \text{Cost}_{\text{instance}}(t) + \beta \cdot \text{Cost}_{\text{TNRP\_penalty}}(t) + \gamma \cdot \text{Penalty}_{\text{delay}}(t) \right)$$
- **Credit Assignment Problem**: Spinning up an expensive multi-GPU instance (e.g., `p3.16xlarge`) incurs an immediate cost penalty, but provides packing capacity for future tasks arriving 10 minutes later. Standard temporal-difference learning (PPO / DQN) struggles with this severe delayed-reward horizon without extensive reward shaping or value baseline engineering.

---

## 3. Training Data & Generalization Requirements

### 3.1 Can a policy learn from 1 trace and 8 snapshots?
**Categorically No.**
- **Overfitting**: An RL agent trained on the single `pai_200` trace would simply memorize the fixed sequence of 200 arrivals. It would function as a hardcoded lookup table rather than a generalized scheduling policy.
- **8 Snapshots**: 8 decision points represent 8 discrete points in time. Training an RL policy on 8 data points is statistically impossible; it provides zero stochastic diversity.

### 3.2 What is realistically needed for generalization?
For an RL policy to generalize across real-world cluster dynamics, the training regime requires:
1. **Diverse Trace Corpus**: Minimum of **50–100 diverse cluster traces** spanning:
   - Varying arrival intensities (Poisson, bursty, diurnal cycles).
   - Diverse GPU-to-CPU task ratios (GPU-heavy training bursts vs. CPU-heavy preprocessing phases).
   - Short vs. long-duration task mixtures.
2. **Workload Generator**: A parametric synthetic trace generator to produce randomized, out-of-distribution training episodes.
3. **Sample Complexity**: Deep RL schedulers in computer systems literature (e.g., Decima, Park, Halikias et al.) typically require **$5 \times 10^5$ to $2 \times 10^6$ environment transition steps** (equivalent to hundreds of thousands of simulated scheduling decisions) to converge to a policy that outperforms tuned heuristics.

---

## 4. Implementation Effort Breakdown (Honest Timeline)

Given that this repository currently has **zero RL infrastructure** (no OpenAI Gym / Gymnasium environment, no vectorized simulator interface, no observation encoders, no RL agent harness):

| Phase | Milestone / Deliverables | Realistic Time |
|---|---|:---:|
| **Phase 1: Environment & Simulator API** | Wrap EVA simulator into a standard `gymnasium.Env` step/reset loop with deterministic state serialization and action masking. | 1.5 – 2 weeks |
| **Phase 2: Neural Architecture** | Implement GNN / Transformer encoder for variable-size instance/task sets; integrate PyTorch / Stable-Baselines3 with action masking. | 1 – 1.5 weeks |
| **Phase 3: Workload Generation** | Build synthetic trace perturbation pipeline to provide hundreds of varied training episodes beyond `pai_200`. | 1 week |
| **Phase 4: Training & Reward Shaping** | Hyperparameter sweeps, PPO/A2C training runs, reward weight tuning ($\alpha, \beta, \gamma$), credit assignment stabilization. | 2 – 3 weeks |
| **Phase 5: Evaluation & Benchmarking** | Benchmark policy against EVA heuristic and CP-SAT bounds across unseen test traces; failure mode analysis. | 1 week |
| **Total Engineering Time** | **Full End-to-End RL Scheduling Framework** | **6.5 – 8.5 weeks** |

---

## 5. Strategic Framing for the Paper

Attempting an RL implementation under project or paper deadlines carries severe scientific and execution risk: RL schedulers frequently fail to beat well-tuned domain heuristics without months of reward engineering.

Instead, this analysis enables a **strong, authoritative framing in the paper**:

1. **Benchmark Triad Established**:
   - **Theoretical Upper Bound**: Exact mathematical optimization via CP-SAT and SCIP (MILP) provides the ground-truth optimal packing and dual bounds.
   - **Rapid Approximation Frontier**: Genetic Algorithms and Simulated Annealing establish how close fast metaheuristics can get (within 0–3% in seconds).
   - **Online Production Heuristic**: EVA's gang scheduler operates in microseconds with zero lookahead.
2. **Framing RL as Future Work**:
   - *"While mathematical programming yields optimal offline decision-point bounds and metaheuristics offer rapid approximations, online scheduling over continuous multi-day traces involves complex temporal trade-offs. Learning-based approaches (such as Graph Reinforcement Learning) offer a promising direction for end-to-end policy learning. However, as demonstrated by our state-space and credit-assignment analysis, doing so generalizably requires vast multi-trace training distributions and complex action-masking graph architectures, representing a rich avenue for future work."*
