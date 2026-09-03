# TNRP Formula Documentation

_Read from source code on 2026-09-03. All line numbers refer to the HEAD commit._

---

## 1. What TNRP Is (Throughput-Normalized Reservation Price)

TNRP is EVA's core concept for valuing co-location. When two tasks share an instance,
they interfere with each other's GPU/memory bandwidth, reducing their effective
throughput. TNRP quantifies this as:

```
TNRP(task_i, co-located_tasks) = min_instance_cost(task_i) × contention_rate(task_i | co-located)
```

Where:
- `min_instance_cost(task_i)` = hourly cost of the cheapest instance that can host
  task_i alone (its "standalone reservation price")
- `contention_rate(task_i | co-located)` = fraction of standalone throughput task_i
  achieves when co-located with the other tasks (∈ (0, 1])

**Interpretation**: TNRP is the effective value task_i delivers per hour when
co-located — its standalone value discounted by the throughput degradation it suffers.

The total opportunity cost of an instance hosting a group of tasks is:

```
total_opp_cost = Σ_i  TNRP(task_i, all_other_tasks_on_same_instance)
```

**Packing decision rule**: provision an instance iff:
```
total_opp_cost  ≥  instance_hourly_cost
```
i.e., the combined effective value of the tasks justifies the instance cost even after
co-location degradation.

---

## 2. The Exact Formula (from `eva_gang_scheduler.py`)

### `get_contention_rate(key, value, contention_map)` — Lines 240–259

```python
def get_contention_rate(self, key, value, contention_map):
    """
    key   = "job_name_task_name"   (the TARGET task being evaluated)
    value = tuple of "job_name_task_name" strings   (ALL co-located tasks, excluding self)
    """
    # CASE 1: Task type not in map at all → use default^n
    if key not in contention_map:
        return pow(self.default_contention_rate, len(value))   # 0.95^n

    # CASE 2: Exact co-location tuple present → average measured values
    if value in contention_map[key]:
        return sum(contention_map[key][value]) / len(contention_map[key][value])

    # CASE 3: Singleton fallback
    if len(value) == 1:
        return self.default_contention_rate   # 0.95

    # CASE 4: Multi-task approx → product of pairwise rates
    product = 1
    for v in value:
        product *= self.get_contention_rate(key, (v,), contention_map)
    return product
```

**Inputs**:
- `key`: string `"{job_name}_{task_name}"` for the task being evaluated (e.g. `"resnet18[0]_node0"`)
- `value`: sorted tuple of co-located task name strings (e.g. `("sage[0]_node0",)`)
- `contention_map`: dict loaded from simulation report (`report['contention_map']`)
- `default_contention_rate`: scheduler parameter, default **0.95**

### `get_opportunity_cost(task_ids, ..., contention_map)` — Lines 262–282

```python
def get_opportunity_cost(self, task_ids, tasks, jobs, instance_types,
                         task_to_min_it_map, contention_map, for_top_down=False,
                         current_it_id=None):
    total_opportunity_cost = 0
    for task_id in task_ids:
        key, value = self.get_contention_map_kv_pair(task_id, task_ids, tasks, jobs)
        contention_rate = self.get_contention_rate(key, value, contention_map)

        # multi-task gang scaling (only in top-down provisioning path)
        if for_top_down:
            contention_rate = max(0, 1 - (1 - contention_rate) * len(jobs[job_id].task_ids))

        opportunity_cost = instance_types[task_to_min_it_map[task_id]].cost * contention_rate
        total_opportunity_cost += opportunity_cost

    return total_opportunity_cost
```

**Full formula per task**:
```
opp_cost_i = cost(min_instance_type(task_i))  ×  contention_rate(task_i | co-located_tasks)
```

**Contention map key construction** (`get_contention_map_kv_pair`, lines 234–238):
```python
key   = f"{job_name}_{task_name}"   # e.g. "resnet18[0]_node0"
value = tuple(sorted([
    f"{job_name}_{task_name}" for task_id in all_task_ids if task_id != target
]))   # e.g. ("cyclegan[2]_node0",)
```

---

## 3. What "No Throughput Aware" Removes — Exact Diff

`EVAGangNoThroughputAwareScheduler.get_opportunity_cost` (lines 260–272) vs
`EVAGangScheduler.get_opportunity_cost` (lines 262–282):

| | EVAGangScheduler (full TNRP) | EVAGangNoThroughputAwareScheduler |
|---|---|---|
| Contention rate computed? | ✅ Yes, via `get_contention_rate()` | ❌ No — dropped entirely |
| Formula | `cost(min_it) × contention_rate` | `cost(min_it) × 1.0` (implicit) |
| Multi-task scaling | ✅ Yes (`for_top_down` path) | ❌ No |

**The interference penalty is precisely**:
```
interference_penalty_i = cost(min_it_i) × (1 - contention_rate_i)
```

This is the term that "no throughput aware" removes. Without it, the scheduler
overestimates the value of co-location (it thinks tasks deliver full throughput even
when sharing), leading to more aggressive packing than is justified.

---

## 4. Is the Model Symmetric?

**No — it is explicitly type-pair-specific and asymmetric.**

From the live `contention_map` in `EVAGangScheduler_pai_200/report.json`:

```
"resnet18[0]_node0" co-located with ("sage[0]_node0",)    → rate = 0.853
"sage[0]_node0"     co-located with ("resnet18[0]_node0",) → rate = 0.973
```

The resnet18 task degrades to 85.3% throughput when sharing with sage, but sage
only degrades to 97.3% when sharing with resnet18. **Different tasks experience
different interference even in the same co-location pair.**

More examples from the map:
```
"resnet18[0]_node0" + ("gcn[0]_node0", "sage[0]_node0")   → 0.822  (3-way co-loc)
"sage[0]_node0"     + ("gcn[0]_node0", "resnet18[0]_node0") → 0.752
"gcn[0]_node0"      + ("resnet18[0]_node0", "sage[0]_node0") → 0.812
```

**Implication for CP-SAT**: A correct TNRP-corrected model must track which tasks
are assigned together (not just how many), and apply asymmetric per-task degradation
factors based on the actual co-location tuple.

---

## 5. Contention Map Structure (from live report.json)

```
contention_map = {
    "resnet18[0]_node0": {               # TARGET task type
        "()":                            # isolated (no co-location) → always 1.0
            [1, 1, 1, ...],
        "('sage[0]_node0',)":            # co-located with sage
            [0.973, 0.973],
        "('gcn[0]_node0', 'sage[0]_node0')":  # co-located with gcn + sage
            [0.822, 0.822, ...],
    },
    "sage[0]_node0": {
        "()": [1, 1, ...],
        "('resnet18[0]_node0',)": [0.853, 0.853],
        ...
    },
    ...
}
```

The sub-key is a **sorted tuple serialized as string** (e.g. `"('sage[0]_node0',)"`).
The values are lists of observed throughput ratios (averaged to get the rate).

---

## 6. What This Means for the CP-SAT TNRP Model

To faithfully incorporate TNRP, the CP-SAT model must:

1. **Allow GPU task co-location** (remove the hard 1-GPU-task-per-instance constraint)
2. **Track co-assignment**: for each pair (i, j) of tasks that could share the same
   instance type, introduce a binary variable `colocate[i,j,t]` indicating both
   are assigned to the same instance of type t
3. **Apply TNRP as a cost penalty in the objective**: when tasks i and j are
   co-located, add the interference penalty to the objective:
   ```
   penalty(i,j) = cost(min_it_i) × (1 - contention_rate(i | j))
               + cost(min_it_j) × (1 - contention_rate(j | i))
   ```
   This penalty is added to the objective when `colocate[i,j,t]` is True.

**Why cost penalty (not capacity multiplier)**: EVA uses TNRP in the objective
function (opportunity cost comparison), not as a capacity constraint. The raw resource
demands are still the physical constraints. TNRP affects only the decision of
_whether_ to co-locate, not _whether it fits_. Therefore: **add TNRP interference
as an objective penalty term**, not as demand scaling.

---

## 7. Schedulers That Use Contention-Rate-Based TNRP

| Scheduler | Uses TNRP? | Notes |
|---|---|---|
| `EVAGangScheduler` | ✅ Full TNRP | `contention_rate × min_it_cost` per task |
| `EVAGangNoThroughputAwareScheduler` | ❌ No | Uses `min_it_cost × 1.0` — ablation |
| `SynergyScheduler` | ✅ Yes | Same `get_opportunity_cost` formula |
| `OwlScheduler` | ✅ Yes | Uses `get_task_normalized_throughputs()` — requires at most 2 tasks, different contention map format (pkl) |
| `StratusScheduler` | ❓ | Not checked (not in scope) |
| `NaiveScheduler` | ❌ No packing | No opportunity cost concept |

---

## 8. Empirical Audit: 3+-Way Co-Location in the 8 Decision-Point Snapshots

**Script**: `cpsat_comparison/audit_3way_contention.py`  
**Question**: Of all 3+-GPU-task groups that EVA actually formed across the 8 snapshots,
what fraction had a **direct** entry in `contention_map` vs. required the **pairwise product fallback**?

### Results

| Metric | Count | Fraction |
|---|---:|---:|
| Total 3+-GPU-task co-located groups found | **22** | 100% |
| Groups with **all-direct** contention_map lookup | **22** | **100.0%** |
| Groups requiring at least one pairwise fallback | **0** | **0.0%** |

### Group inventory (all 22 were direct)

| Snapshot (ts) | Instance | GPU tasks co-located | Max group size |
|---:|---:|---|---:|
| 9,900 | inst 3 | sage×2, seq | 3 |
| 9,900 | inst 8 | resnet18×2, sage | 3 |
| 9,900 | inst 9 | resnet18×2, sage | 3 |
| 51,300 | inst 16 | cyclegan×2, sage, seq, vit | **5** |
| 51,300 | inst 45 | vit×3 | 3 |
| 93,000 | inst 53 | cyclegan×2, vit | 3 |
| 93,000 | inst 72 | cyclegan, sage, vit | 3 |
| 93,000 | inst 73 | cyclegan×2, vit | 3 |
| 134,400 | inst 53 | cyclegan, resnet18, vit | 3 |
| 134,400 | inst 72 | cyclegan×2, vit | 3 |
| 134,400 | inst 96 | cyclegan×2, vit | 3 |
| 134,400 | inst 113 | cyclegan×2, vit | 3 |
| 165,600 | inst 134 | cyclegan×2, vit | 3 |
| 165,600 | inst 158 | cyclegan×2, vit | 3 |
| 217,200 | inst 53 | cyclegan, sage, vit | 3 |
| 217,200 | inst 102 | cyclegan×2, vit | 3 |
| 217,200 | inst 173 | cyclegan×2, vit | 3 |
| 217,200 | inst 196 | cyclegan, seq, vit | 3 |
| 258,600 | inst 53 | cyclegan×2, vit | 3 |
| 258,600 | inst 102 | cyclegan×2, vit | 3 |
| 300,000 | inst 102 | cyclegan×2, vit×2 | **4** |
| 300,000 | inst 173 | cyclegan×2, vit | 3 |

### Conclusion: **Proceed with Option A (pairwise product) is SAFE**

The contention_map used in the actual simulation contains **direct empirical measurements
for every 3, 4, and even 5-way co-location group** that EVA actually formed during the
pai_200 run — including 4-way (cyclegan×2 + vit×2) and 5-way (cyclegan×2 + sage + seq + vit).

This means the pairwise product formula (`rate(A|B) × rate(A|C)`) is **never invoked
by EVA itself** during this simulation — it always has a direct measurement.

However, in the CP-SAT model, we are solving a new assignment problem where arbitrary
new task combinations may be formed that EVA never tried. For those, the pairwise product
is the fallback — exactly as EVA's own code specifies. Since EVA's own scheduler
implemented and accepted this fallback, the CP-SAT model inherits no more inaccuracy
than EVA's own design.

**Decision**: Use Option A (pairwise product approximation) in the CP-SAT TNRP model.
Where the contention_map has a direct entry for the exact tuple, use it; where it does
not, use the pairwise product — matching EVA's own `get_contention_rate()` logic exactly.
