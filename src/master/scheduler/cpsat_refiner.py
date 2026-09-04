"""
cpsat_refiner.py    CP-SAT refinement module for EVAGangScheduler.

Design contract
---------------
* Receives Eva's current scheduling state and Eva's already-validated
  planned_config.
* Builds a CP-SAT model that mirrors Eva's net-saving objective exactly:
      net_saving = provision_saving_per_sec * T - migration_cost
  using the same helper functions as EVAGangScheduler.
* Returns (result_config, log_entry).
  result_config is the CP-SAT solution if feasible AND strictly better than
  Eva's plan; otherwise Eva's plan is returned unchanged.

OBJECTIVE COMPONENTS (Eva-aligned):
  A. Standalone opp cost (constant  does not affect optimisation direction)
  B. Pairwise TNRP interference penalty  (subtracted)
  C. Actual instance provisioning cost   (subtracted)
  D. Job-level migration cost            (subtracted, once per moved job)
  E. New-instance 300-second startup cost (subtracted)

LINEARISATION / APPROXIMATION:
  L1. For 3+ co-located GPU tasks, pairwise sum approximates Eva's product
      formula (Eva's own fallback when no exact tuple in contention_map).
      This makes CP-SAT slightly conservative (under-estimates dense packing
      gains) rather than over-optimistic.
  L2. Horizon T is frozen at Eva's value for this scheduling round.
  L3. Migration is per JOB, not per task (matching Eva exactly).

Do NOT modify EVAGangScheduler, master.py, simulator.py, or any RPC layer.
"""

import copy
import logging
import time as time_module
from typing import Dict, List, Optional, Tuple, Any

import numpy as np

logger = logging.getLogger(__name__)

# Integer scaling: costs in $/hr ? scaled by SCALE to get integer units
SCALE = 1_000_000
STARTUP_PENALTY_SECONDS = 300   # Eva's startup cost window (seconds)


# -----------------------------------------------------------------------------
# Contention helpers  (replicate Eva's exact logic, no imports from Eva)
# -----------------------------------------------------------------------------

def _task_label(task_id, tasks, jobs):
    """Return 'jobname_taskname' key used in contention_map (matches Eva)."""
    return f"{jobs[tasks[task_id].job_id].name}_{tasks[task_id].name}"


def _get_contention_rate(key, value, contention_map, default_rate=0.95):
    """
    Exact copy of EVAGangScheduler.get_contention_rate().
    key   : str    target task label
    value : tuple  sorted co-located task labels (excluding target)
    """
    if key not in contention_map:
        return pow(default_rate, len(value))
    if value in contention_map[key]:
        vals = contention_map[key][value]
        return sum(vals) / len(vals)
    if len(value) == 1:
        return default_rate
    product = 1.0
    for v in value:
        product *= _get_contention_rate(key, (v,), contention_map, default_rate)
    return product


def _pairwise_tnrp_penalty(ti, tj, tasks, jobs,
                            task_to_min_it_map, instance_types,
                            contention_map, default_rate=0.95):
    """
    TNRP penalty for co-locating tasks ti and tj, in $/hr.
        penalty = cost_i*(1-rate(i|j)) + cost_j*(1-rate(j|i))
    Matches decision_point_comparison_tnrp.md formula exactly.
    """
    li = _task_label(ti, tasks, jobs)
    lj = _task_label(tj, tasks, jobs)
    ri = _get_contention_rate(li, (lj,), contention_map, default_rate)
    rj = _get_contention_rate(lj, (li,), contention_map, default_rate)
    ci = instance_types[task_to_min_it_map[ti]].cost
    cj = instance_types[task_to_min_it_map[tj]].cost
    return ci * (1.0 - ri) + cj * (1.0 - rj)


# -----------------------------------------------------------------------------
# Eva objective evaluator (uses Eva helper functions via import)
# -----------------------------------------------------------------------------

def _eva_objective(planned_config, current_config,
                   tasks, jobs, instances, instance_types,
                   task_to_min_it_map, contention_map,
                   horizon_T, default_rate=0.95):
    """
    Returns (net_saving, provision_saving_per_sec, migration_cost).
    Calls EVAGangScheduler helpers to stay exactly in sync with Eva.
    """
    from master.scheduler.eva_gang_scheduler import EVAGangScheduler
    sched = EVAGangScheduler(default_contention_rate=default_rate)

    actual_ps = sched.get_config_cost(planned_config, instances, instance_types)

    opp_raw = 0.0
    for t_ids in planned_config.values():
        opp_raw += sched.get_opportunity_cost(
            t_ids, tasks, jobs, instance_types,
            task_to_min_it_map, contention_map, for_top_down=False)
    opp_ps = opp_raw / 3600.0

    prov_saving = opp_ps - actual_ps
    mig_cost    = sched.calculate_migration_cost(
        current_config, planned_config, jobs, tasks, instance_types)
    net_saving  = prov_saving * horizon_T - mig_cost
    return net_saving, prov_saving, mig_cost


# -----------------------------------------------------------------------------
# Validation
# -----------------------------------------------------------------------------

def validate_config(config, candidate_task_ids, tasks, instances, instance_types):
    """
    Returns (ok: bool, msg: str).
    Checks: single assignment, capacity, family compatibility.
    """
    assigned = {tid: 0 for tid in candidate_task_ids}
    for inst_key, t_ids in config.items():
        if isinstance(inst_key, tuple):
            it_id = inst_key[1]
        else:
            it_id = instances[inst_key].instance_type_id
        it   = instance_types[it_id]
        fam  = it.family
        cap  = it.capacity
        cum  = np.zeros(len(cap))
        for tid in t_ids:
            if fam not in tasks[tid].demand_dict:
                return False, f"Task {tid} incompatible with family {fam}"
            cum = cum + tasks[tid].demand_dict[fam]
            if tid in assigned:
                assigned[tid] += 1
        if np.any(cum > cap + 1e-6):
            return False, f"Capacity exceeded on {inst_key}"
    for tid, cnt in assigned.items():
        if cnt != 1:
            return False, f"Task {tid} assigned {cnt} times"
    return True, "OK"


# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------

def refine_with_cpsat(
    eva_planned_config: dict,
    current_config: dict,
    candidate_task_ids: list,
    fixed_config: dict,
    tasks: dict,
    jobs: dict,
    instances: dict,
    instance_types: dict,
    task_to_min_it_map: dict,
    contention_map: dict,
    horizon_T: float,
    sim_time,
    time_limit_sec: float = 5.0,
    default_contention_rate: float = 0.95,
    next_pseudo_id_start: int = -1000,
):
    """
    Run CP-SAT refinement over Eva's planned_config.

    Returns
    -------
    (result_config, log_entry)
    result_config: eva_planned_config or CP-SAT solution (same schema)
    log_entry    : dict with all diagnostic fields
    """
    t_total_start = time_module.time()

    # -- Baseline Eva objective ---------------------------------------------
    eva_net, eva_prov, eva_mig = _eva_objective(
        eva_planned_config, current_config,
        tasks, jobs, instances, instance_types,
        task_to_min_it_map, contention_map, horizon_T, default_contention_rate)

    log = {
        "sim_time":                    sim_time,
        "num_candidate_tasks":         len(candidate_task_ids),
        "num_existing_instances":      sum(1 for i in instances
                                           if instances[i].task_assignable),
        "eva_net_saving":              round(eva_net,  6),
        "eva_provision_saving_per_sec":round(eva_prov, 8),
        "eva_migration_cost":          round(eva_mig,  6),
        "cpsat_net_saving":            None,
        "cpsat_provision_saving_per_sec": None,
        "cpsat_migration_cost":        None,
        "objective_improvement":       None,
        "solver_status":               "NOT_RUN",
        "solver_best_bound":           None,
        "solver_wall_time_sec":        None,
        "plan_selected":               "EVA",
        "notes":                       [],
    }

    # -- Early exits -------------------------------------------------------
    if not candidate_task_ids:
        log["solver_status"] = "SKIPPED_NO_TASKS"
        return eva_planned_config, log

    if horizon_T is None or (isinstance(horizon_T, float) and
                              (np.isnan(horizon_T) or horizon_T <= 0)):
        log["solver_status"] = "SKIPPED_NO_HORIZON"
        log["notes"].append("horizon_T unavailable")
        return eva_planned_config, log

    try:
        from ortools.sat.python import cp_model
    except ImportError:
        log["solver_status"] = "IMPORT_ERROR"
        log["notes"].append("ortools not installed")
        return eva_planned_config, log

    # -- Build slot list ---------------------------------------------------
    # Slot = one candidate "bin" (existing instance or one new-provision slot
    # per instance type).
    slots = []
    for inst_id, inst in instances.items():
        if not inst.task_assignable:
            continue
        it_id = inst.instance_type_id
        it = instance_types[it_id]
        slots.append({
            "s": len(slots),
            "it_id": it_id,
            "family": it.family,
            "capacity": it.capacity.tolist(),
            "cost_hr": it.cost,
            "existing_inst_id": inst_id,
            "is_new": False,
        })

    seen_new = set()
    for it_id, it in instance_types.items():
        if it_id in seen_new:
            continue
        seen_new.add(it_id)
        slots.append({
            "s": len(slots),
            "it_id": it_id,
            "family": it.family,
            "capacity": it.capacity.tolist(),
            "cost_hr": it.cost,
            "existing_inst_id": None,
            "is_new": True,
        })

    n_slots = len(slots)
    n_tasks = len(candidate_task_ids)
    tidx    = {tid: i for i, tid in enumerate(candidate_task_ids)}

    # -- Pre-compute demands (family-keyed) --------------------------------
    task_dem = {tid: tasks[tid].demand_dict for tid in candidate_task_ids}

    # -- Pre-compute pairwise TNRP penalties -------------------------------
    pair_pen = {}
    tlist = candidate_task_ids
    for ii in range(len(tlist)):
        for jj in range(ii + 1, len(tlist)):
            p = _pairwise_tnrp_penalty(
                tlist[ii], tlist[jj], tasks, jobs,
                task_to_min_it_map, instance_types,
                contention_map, default_contention_rate)
            if p > 1e-9:
                pair_pen[(ii, jj)] = p

    # -- Pre-compute job migration costs -----------------------------------
    curr_place = {}
    for iid, t_ids in current_config.items():
        for tid in t_ids:
            curr_place[tid] = iid

    cand_jobs = set(tasks[tid].job_id for tid in candidate_task_ids)
    job_mig   = {jid: jobs[jid].get_migration_cost(tasks) for jid in cand_jobs}

    # -- Build CP-SAT model ------------------------------------------------
    model = cp_model.CpModel()

    # Decision vars: x[t_idx, s_idx] = 1 iff task t on slot s
    x = {(ti, si): model.NewBoolVar(f"x_{ti}_{si}")
         for ti in range(n_tasks) for si in range(n_slots)}

    # y[s_idx] = 1 iff slot s is used
    y = {si: model.NewBoolVar(f"y_{si}") for si in range(n_slots)}

    # Constraint: each task assigned to exactly one slot
    for ti in range(n_tasks):
        model.Add(sum(x[(ti, si)] for si in range(n_slots)) == 1)

    # Constraint: capacity per resource dimension
    DSCALE = 1000  # demand scaling to avoid floats in CP-SAT
    for si, sl in enumerate(slots):
        fam = sl["family"]
        cap = sl["capacity"]
        for dim in range(len(cap)):
            demand_terms = []
            for ti, tid in enumerate(candidate_task_ids):
                dem = task_dem[tid].get(fam, None)
                if dem is None:
                    model.Add(x[(ti, si)] == 0)
                    continue
                demand_terms.append(x[(ti, si)] * int(round(dem[dim] * DSCALE)))
            cap_val = int(round(cap[dim] * DSCALE))
            if demand_terms:
                model.Add(sum(demand_terms) <= cap_val)
            # y[si] = 0 ? no tasks (implicit from x assignment constraint)

    # Constraint: family compatibility (hard block)
    for si, sl in enumerate(slots):
        fam = sl["family"]
        for ti, tid in enumerate(candidate_task_ids):
            if fam not in task_dem[tid]:
                model.Add(x[(ti, si)] == 0)

    # Constraint: y[s] >= x[t,s]
    for si in range(n_slots):
        for ti in range(n_tasks):
            model.Add(y[si] >= x[(ti, si)])

    # Co-location binary: z[(ii,jj,si)] = x[ii,si] AND x[jj,si]
    z = {}
    for (ii, jj), pen_hr in pair_pen.items():
        for si in range(n_slots):
            v = model.NewBoolVar(f"z_{ii}_{jj}_{si}")
            model.AddBoolAnd([x[(ii, si)], x[(jj, si)]]).OnlyEnforceIf(v)
            model.AddBoolOr([x[(ii, si)].Not(),
                             x[(jj, si)].Not()]).OnlyEnforceIf(v.Not())
            z[(ii, jj, si)] = v

    # Migration vars: moved_job[jid] = 1 iff any task of job moves
    task_moved = {}
    for ti, tid in enumerate(candidate_task_ids):
        curr_inst = curr_place.get(tid, None)
        same_slots = [si for si, sl in enumerate(slots)
                      if sl["existing_inst_id"] == curr_inst]
        tm = model.NewBoolVar(f"tm_{ti}")
        task_moved[ti] = tm
        if curr_inst is None:
            model.Add(tm == 0)   # new task  no migration cost
        elif not same_slots:
            model.Add(tm == 1)   # current instance no longer available
        else:
            stayed = model.NewBoolVar(f"stayed_{ti}")
            model.Add(sum(x[(ti, si)] for si in same_slots) >= 1).OnlyEnforceIf(stayed)
            model.Add(sum(x[(ti, si)] for si in same_slots) == 0).OnlyEnforceIf(stayed.Not())
            model.Add(tm == stayed.Not())

    moved_job_var = {}
    for jid in cand_jobs:
        task_tidxs = [tidx[tid] for tid in jobs[jid].task_ids if tid in tidx]
        if not task_tidxs:
            continue
        mj = model.NewBoolVar(f"mj_{jid}")
        moved_job_var[jid] = mj
        model.AddBoolOr([task_moved[ti] for ti in task_tidxs]).OnlyEnforceIf(mj)
        model.AddBoolAnd([task_moved[ti].Not() for ti in task_tidxs]).OnlyEnforceIf(mj.Not())

    # -- Objective ---------------------------------------------------------
    # We maximise (net_saving * SCALE * T_hr), dropping additive constants:
    #   + sum_t cost(min_it_t) * T_hr   [constant, omitted  doesn't change opt]
    #   - sum_{pairs (i,j) co-located} penalty(i,j) * T_hr
    #   - sum_s  cost(slot_s) * y[s] * T_hr
    #   - sum_j  mig_cost(j) * moved_job[j]
    #   - sum_s_new  startup_cost(s) * y[s]

    T_hr = horizon_T / 3600.0
    FS   = max(1, int(round(SCALE * T_hr)))   # full scale: SCALE * T_hr

    obj_terms = []

    # Pairwise interference penalty (subtracted from opp cost * T)
    for (ii, jj, si), zv in z.items():
        pen_hr = pair_pen[(ii, jj)]
        coeff  = -int(round(pen_hr * FS))
        if coeff:
            obj_terms.append(coeff * zv)

    # Actual instance provisioning cost * T (subtracted from net saving)
    for si, sl in enumerate(slots):
        coeff = -int(round(sl["cost_hr"] * FS))
        if coeff:
            obj_terms.append(coeff * y[si])

    # Job migration cost (subtracted; not multiplied by T  it's one-off)
    for jid, mj_var in moved_job_var.items():
        mig = job_mig.get(jid, 0.0)
        coeff = -int(round(mig * SCALE))
        if coeff:
            obj_terms.append(coeff * mj_var)

    # New-instance startup penalty: cost_hr * 300/3600 (one-off)
    for si, sl in enumerate(slots):
        if sl["is_new"]:
            startup = sl["cost_hr"] * STARTUP_PENALTY_SECONDS / 3600.0
            coeff   = -int(round(startup * SCALE))
            if coeff:
                obj_terms.append(coeff * y[si])

    if obj_terms:
        model.Maximize(sum(obj_terms))
    else:
        model.Maximize(model.NewIntVar(0, 0, "dummy"))

    # -- Eva warm-start ----------------------------------------------------
    def _slot_for_eva_key(k):
        if isinstance(k, tuple):
            it_id = k[1]
            for si, sl in enumerate(slots):
                if sl["is_new"] and sl["it_id"] == it_id:
                    return si
            return None
        for si, sl in enumerate(slots):
            if sl["existing_inst_id"] == k:
                return si
        return None

    hint_x = {(ti, si): 0 for ti in range(n_tasks) for si in range(n_slots)}
    for inst_key, t_ids in eva_planned_config.items():
        si = _slot_for_eva_key(inst_key)
        if si is None:
            continue
        for tid in t_ids:
            if tid in tidx:
                hint_x[(tidx[tid], si)] = 1

    for (ti, si), val in hint_x.items():
        model.AddHint(x[(ti, si)], val)

    # -- Solve -------------------------------------------------------------
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds     = time_limit_sec
    solver.parameters.log_search_progress     = False
    solver.parameters.num_search_workers      = 1

    t_s = time_module.time()
    status = solver.Solve(model)
    wall   = time_module.time() - t_s

    STATUS = {
        cp_model.OPTIMAL:       "OPTIMAL",
        cp_model.FEASIBLE:      "FEASIBLE",
        cp_model.INFEASIBLE:    "INFEASIBLE",
        cp_model.UNKNOWN:       "UNKNOWN",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
    }
    log["solver_status"]        = STATUS.get(status, str(status))
    log["solver_wall_time_sec"] = round(wall, 3)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        log["plan_selected"] = "EVA"
        log["solver_wall_time_sec"] = round(time_module.time() - t_total_start, 3)
        return eva_planned_config, log

    try:
        log["solver_best_bound"] = solver.BestObjectiveBound()
    except Exception:
        pass

    # -- Decode solution ---------------------------------------------------
    slot_tasks = {si: [] for si in range(n_slots)}
    for ti, tid in enumerate(candidate_task_ids):
        for si in range(n_slots):
            if solver.Value(x[(ti, si)]) == 1:
                slot_tasks[si].append(tid)
                break

    cpsat_config = copy.deepcopy(fixed_config)
    pseudo_id    = next_pseudo_id_start
    new_it_map   = {}  # it_id -> pseudo_id allocated

    for si, sl in enumerate(slots):
        t_ids = slot_tasks[si]
        if not t_ids:
            continue
        if sl["is_new"]:
            it_id = sl["it_id"]
            if it_id not in new_it_map:
                new_it_map[it_id] = pseudo_id
                pseudo_id -= 1
            key = (new_it_map[it_id], it_id)
        else:
            key = sl["existing_inst_id"]
        cpsat_config.setdefault(key, []).extend(t_ids)

    # -- Validate ----------------------------------------------------------
    ok, msg = validate_config(cpsat_config, candidate_task_ids,
                              tasks, instances, instance_types)
    if not ok:
        log["solver_status"] += f"_INVALID({msg})"
        log["plan_selected"]  = "EVA"
        log["solver_wall_time_sec"] = round(time_module.time() - t_total_start, 3)
        return eva_planned_config, log

    # -- Compare with Eva --------------------------------------------------
    cnet, cprov, cmig = _eva_objective(
        cpsat_config, current_config,
        tasks, jobs, instances, instance_types,
        task_to_min_it_map, contention_map, horizon_T, default_contention_rate)

    log["cpsat_net_saving"]               = round(cnet,  6)
    log["cpsat_provision_saving_per_sec"] = round(cprov, 8)
    log["cpsat_migration_cost"]           = round(cmig,  6)
    log["objective_improvement"]          = round(cnet - eva_net, 6)

    if cnet > eva_net + 1e-9:
        log["plan_selected"] = "CPSAT"
        result = cpsat_config
    else:
        log["plan_selected"] = "EVA"
        result = eva_planned_config

    log["solver_wall_time_sec"] = round(time_module.time() - t_total_start, 3)
    return result, log
