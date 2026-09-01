import os
import json
import time
from ortools.sat.python import cp_model

def load_data():
    with open("src/simulation/config/ec2_config_virt.json", "r") as f:
        ec2_config = json.load(f)
    
    with open("src/pai_trace/traces/pai_200.json", "r") as f:
        pai_200 = json.load(f)
        
    instance_types = []
    for it_name, it_info in ec2_config["instance_types"].items():
        instance_types.append({
            "name": it_name,
            "capacity": it_info["capacity"], # [GPU, CPU, RAM]
            "cost": it_info["cost"]
        })
        
    tasks = []
    # Using job index mapping to make sure it's ordered properly
    for job_id in sorted([int(k) for k in pai_200.keys()]):
        job_info = pai_200[str(job_id)]
        task_id = list(job_info["tasks"].keys())[0]
        task_info = job_info["tasks"][task_id]
        demand = task_info["demand"]["any"] # [GPU, CPU, RAM]
        tasks.append({
            "name": f"{job_info['name']}_{task_id}",
            "demand": demand
        })
        
    return instance_types, tasks

def solve_bin_packing(instance_types, tasks):
    model = cp_model.CpModel()
    
    N = len(tasks)
    T = len(instance_types)
    
    # Scale cost to integer (multiply by 100,000)
    COST_SCALE = 100000
    
    # Variables
    print("Creating variables...")
    x = {}
    for i in range(N):
        for j in range(N):
            x[i, j] = model.NewBoolVar(f"x_{i}_{j}")
            
    y = {}
    for j in range(N):
        for t in range(T):
            y[j, t] = model.NewBoolVar(f"y_{j}_{t}")
            
    z = {}
    for j in range(N):
        z[j] = model.NewBoolVar(f"z_{j}")
        
    print("Adding constraints...")
    # 1. Each task assigned to exactly one instance
    for i in range(N):
        model.AddExactlyOne([x[i, j] for j in range(N)])
        
    # 2. If instance used, exactly one type
    for j in range(N):
        model.Add(sum(y[j, t] for t in range(T)) == z[j])
        
    # 3. Task can only be assigned to used instances
    for i in range(N):
        for j in range(N):
            model.AddImplication(x[i, j], z[j])
            
    # 4. Capacity constraints
    for j in range(N):
        for r in range(3): # 0: GPU, 1: CPU, 2: RAM
            demand_sum = sum(tasks[i]["demand"][r] * x[i, j] for i in range(N))
            capacity_sum = sum(instance_types[t]["capacity"][r] * y[j, t] for t in range(T))
            model.Add(demand_sum <= capacity_sum)
            
    # 5. Symmetry breaking
    for j in range(N - 1):
        model.Add(z[j] >= z[j+1])
        
    print("Setting objective...")
    # Objective: Minimize total cost
    total_cost = sum(
        y[j, t] * int(instance_types[t]["cost"] * COST_SCALE)
        for j in range(N)
        for t in range(T)
    )
    model.Minimize(total_cost)
    
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 1800.0 # 30 minutes
    solver.parameters.log_search_progress = True
    
    print("Starting solver...")
    start_time = time.time()
    status = solver.Solve(model)
    solve_time = time.time() - start_time
    
    if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        obj_value = solver.ObjectiveValue() / COST_SCALE
        best_bound = solver.BestObjectiveBound() / COST_SCALE
        print(f"Status: {solver.StatusName(status)}")
        print(f"Objective (Total Cost): {obj_value}")
        print(f"Best Bound: {best_bound}")
        print(f"Solve Time: {solve_time:.2f} s")
        
        assignment = []
        for j in range(N):
            if solver.Value(z[j]):
                assigned_type = None
                for t in range(T):
                    if solver.Value(y[j, t]):
                        assigned_type = instance_types[t]["name"]
                        break
                
                assigned_tasks = []
                for i in range(N):
                    if solver.Value(x[i, j]):
                        assigned_tasks.append(tasks[i]["name"])
                        
                assignment.append({
                    "instance_id": j,
                    "type": assigned_type,
                    "tasks": assigned_tasks
                })
                
        return solver.StatusName(status), obj_value, best_bound, solve_time, assignment
    else:
        print(f"Status: {solver.StatusName(status)}")
        return solver.StatusName(status), None, None, solve_time, []

def main():
    instance_types, tasks = load_data()
    status, cost, best_bound, solve_time, assignment = solve_bin_packing(instance_types, tasks)
    
    results = [{
        "scheduler name": "CP-SAT",
        "total cost": cost,
        "best bound": best_bound,
        "runtime": solve_time,
        "solve_status": status,
        "assignment": assignment
    }]
    
    with open("cpsat_comparison/cpsat_results.json", "w") as f:
        json.dump(results, f, indent=4)
        
    print("Results saved to cpsat_comparison/cpsat_results.json")

if __name__ == "__main__":
    main()
