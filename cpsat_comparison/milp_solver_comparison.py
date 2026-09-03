import os
import json
import ast
import time
from pyscipopt import Model as ScipModel, quicksum

# Import data and helpers from decision_point_analysis_tnrp
from decision_point_analysis_tnrp import (
    instances, tasks_data, jobs_data, inst_types, cm, it_by_name,
    cpsat_types, ec2_cfg, instance_active_at, committed_tasks_at,
    task_demand, snapshot_at, task_label, get_contention_rate,
    tnrp_penalty_pair, build_tnrp_penalty_matrix, DEFAULT_RATE, COST_SCALE
)

OUTPUT_JSON_PATH = "cpsat_comparison/milp_results.json"
OUTPUT_MD_PATH = "notes/milp_comparison.md"

def milp_solve_tnrp(task_subset, task_labels, time_limit_s=60.0):
    N = len(task_subset)
    T = len(cpsat_types)

    min_it_costs = []
    for i in range(N):
        d = task_subset[i]["demand"]
        best = None
        for ct in cpsat_types:
            cap = ct["capacity"]
            if all(d[r] <= cap[r] for r in range(3)):
                if best is None or ct["cost"] < best:
                    best = ct["cost"]
        min_it_costs.append(best if best is not None else 0.0)

    P, gpu_indices = build_tnrp_penalty_matrix(task_subset, task_labels, min_it_costs)

    model = ScipModel("TNRP_MILP")
    model.setRealParam("limits/time", time_limit_s)
    model.hideOutput()

    cnt = {}
    u = {}
    for t in range(T):
        cnt[t] = model.addVar(vtype="I", lb=0, name=f"cnt_{t}")
    for i in range(N):
        for t in range(T):
            u[i, t] = model.addVar(vtype="B", name=f"u_{i}_{t}")

    for i in range(N):
        model.addCons(quicksum(u[i, t] for t in range(T)) == 1)

    for t in range(T):
        cap = cpsat_types[t]["capacity"]
        for r in range(3):
            model.addCons(quicksum(task_subset[i]["demand"][r] * u[i, t] for i in range(N)) <= cap[r] * cnt[t])

    for i in range(N):
        feasible = []
        for t in range(T):
            cap = cpsat_types[t]["capacity"]
            if all(task_subset[i]["demand"][r] <= cap[r] for r in range(3)):
                feasible.append(t)
            else:
                model.addCons(u[i, t] == 0)
        if not feasible:
            raise ValueError(f"Task {task_subset[i]['name']} cannot fit on any instance type!")

    for t in range(T):
        for i in range(N):
            model.addCons(cnt[t] >= u[i, t])

    penalty_terms = []
    for (i, j), pen in P.items():
        if pen <= 0:
            continue
        
        shared_ij = model.addVar(vtype="B", name=f"shared_{i}_{j}")
        can_share = False
        
        for t in range(T):
            cap = cpsat_types[t]["capacity"]
            d_i = task_subset[i]["demand"]
            d_j = task_subset[j]["demand"]
            if not (all(d_i[r] <= cap[r] for r in range(3)) and
                    all(d_j[r] <= cap[r] for r in range(3))):
                continue
            if all(d_i[r] + d_j[r] <= cap[r] * 2 for r in range(3)):
                model.addCons(shared_ij >= u[i, t] + u[j, t] - 1)
                can_share = True
                
        if not can_share:
            model.addCons(shared_ij == 0)
            
        penalty_terms.append((pen, shared_ij))

    instance_cost = quicksum(cnt[t] * cpsat_types[t]["cost"] for t in range(T))
    penalty_cost = quicksum(coeff * var for coeff, var in penalty_terms)
    model.setObjective(instance_cost + penalty_cost, "minimize")

    t0 = time.time()
    model.optimize()
    elapsed = time.time() - t0

    status = model.getStatus()

    if status in ("optimal", "feasible", "timelimit"):
        if model.getSols():
            raw_obj = model.getObjVal()
            raw_bound = model.getDualbound()
            
            inst_hr = sum(model.getVal(cnt[t]) * cpsat_types[t]["cost"] for t in range(T))
            pen_hr = sum(coeff * model.getVal(var) for coeff, var in penalty_terms)
            
            cost_hr = raw_obj
            bound_hr = raw_bound
            
            assignment = []
            for t in range(T):
                cnt_val = int(round(model.getVal(cnt[t])))
                if cnt_val > 0:
                    assigned = [task_subset[i]["name"] for i in range(N) if round(model.getVal(u[i, t])) == 1]
                    assignment.append({
                        "instance_type": cpsat_types[t]["name"],
                        "count": cnt_val,
                        "tasks": assigned
                    })
            
            return cost_hr, bound_hr, inst_hr, pen_hr, status, elapsed, assignment

    return None, None, None, None, status, elapsed, []

def main():
    with open("cpsat_comparison/decision_point_snapshots_tnrp.json", "r") as f:
        cpsat_results = json.load(f)
        
    milp_results = []
    
    for r in cpsat_results:
        t = r["timestamp"]
        print(f"\n--- Snapshot t = {t} ---")
        active_ids, task_ids, eva_cost_hr, task_demands, assignment_map = snapshot_at(t)
        
        task_labels_list = [task_label(td["task_id"]) for td in task_demands]
        
        cost_hr, bound_hr, inst_hr, pen_hr, status, solve_time, milp_assign = milp_solve_tnrp(
            task_demands, task_labels_list, time_limit_s=60.0
        )
        
        gap_pct = None
        if cost_hr is not None and bound_hr is not None and cost_hr > 0:
            if bound_hr > cost_hr:
                bound_hr = cost_hr
            gap_pct = 100.0 * (cost_hr - bound_hr) / cost_hr
            
        r_milp = r.copy()
        r_milp["milp_cost_tnrp"] = cost_hr
        r_milp["milp_bound_tnrp"] = bound_hr
        r_milp["milp_inst_cost_tnrp"] = inst_hr
        r_milp["milp_pen_cost_tnrp"] = pen_hr
        r_milp["milp_status_tnrp"] = status
        r_milp["milp_solve_time_tnrp"] = solve_time
        r_milp["milp_gap_pct_tnrp"] = gap_pct
        r_milp["milp_assignment_tnrp"] = milp_assign
        milp_results.append(r_milp)
        
        print(f"CP-SAT Cost: {r.get('cpsat_cost_tnrp')}, Status: {r.get('cpsat_status_tnrp')}")
        print(f"MILP   Cost: {cost_hr}, Status: {status}")

    with open(OUTPUT_JSON_PATH, "w") as f:
        json.dump(milp_results, f, indent=2)
        
    out = []
    out.append("# EVA vs CP-SAT vs MILP (SCIP): Decision-Point Snapshot Comparison")
    out.append("")
    out.append("This report compares the TNRP-corrected CP-SAT model to an identical MILP formulation solved via PySCIPOpt (since Gurobi was not licensed).")
    out.append("")
    out.append("| Timestamp (s) | Tasks (GPU/CPU) | EVA $/hr | **CP-SAT TNRP $/hr** | **CP-SAT Gap %** | **MILP TNRP $/hr** | **MILP Gap %** | Solver |")
    out.append("|---:|---:|---:|---:|---:|---:|---:|---|")
    
    cpsat_optimal_count = 0
    milp_optimal_count = 0
    
    for r in milp_results:
        t = r["timestamp"]
        tc = f"{r['task_count']} ({r['gpu_task_count']}/{r['cpu_task_count']})"
        eva = f"{r['eva_cost']:.4f}"
        
        c_cost = r.get("cpsat_cost_tnrp")
        c_gap = r.get("gap_pct_tnrp")
        m_cost = r.get("milp_cost_tnrp")
        m_gap = r.get("milp_gap_pct_tnrp")
        
        c_status = r.get("cpsat_status_tnrp")
        m_status = r.get("milp_status_tnrp")
        
        if c_status == "OPTIMAL": cpsat_optimal_count += 1
        if m_status == "optimal": milp_optimal_count += 1
        
        def fmt(v): return f"{v:.4f}" if v is not None else "n/a"
        def fmt_gap(v): return (("+" if v >= 0 else "") + f"{v:.2f}%") if v is not None else "n/a"
        
        out.append(f"| {t} | {tc} | {eva} | **{fmt(c_cost)}** | **{fmt_gap(c_gap)}** | **{fmt(m_cost)}** | **{fmt_gap(m_gap)}** | SCIP |")
        
    out.append("")
    out.append("## Summary")
    out.append(f"- CP-SAT reached OPTIMAL on {cpsat_optimal_count} snapshots.")
    out.append(f"- MILP (SCIP) reached OPTIMAL on {milp_optimal_count} snapshots.")
    
    with open(OUTPUT_MD_PATH, "w") as f:
        f.write("\n".join(out) + "\n")

if __name__ == "__main__":
    main()
