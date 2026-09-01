import os
import json
import numpy as np

base_dir = "src/simulation_experiments"
schedulers = [
    "NaiveScheduler",
    "EVAGangScheduler",
    "StratusScheduler",
    "OwlScheduler",
    "SynergyScheduler"
]

def get_max_time(report):
    max_time = 0
    for instance in report['instances'].values():
        for session in instance['active_session_queue']:
            end_time = session['shut_down_end_time'] or max_time
            max_time = max(max_time, end_time)
        for history in instance['history']:
            max_time = max(max_time, history['timestamp'])
    for job in report['jobs'].values():
        for history in job['history']:
            max_time = max(max_time, history['timestamp'])
    return int(np.ceil(max_time))

def is_instance_active(instance, time):
    for session in instance['active_session_queue']:
        if session['worker_register_start_time'] <= time <= (session['shut_down_start_time'] or time):
            return True
    return False

def calculate_total_cost(report):
    max_time = get_max_time(report)
    total_cost = 0.0
    for time in range(max_time):
        for instance_id, instance in report['instances'].items():
            if is_instance_active(instance, time):
                it_id = instance['instance_type_id']
                total_cost += report['instance_types'][str(it_id)]['cost'] / 3600.0
    return total_cost, max_time

results = {}
for s in schedulers:
    report_path = os.path.join(base_dir, f"{s}_pai_200", "report.json")
    if os.path.exists(report_path):
        with open(report_path, 'r') as f:
            report = json.load(f)
        cost, max_time = calculate_total_cost(report)
        sim_hours = max_time / 3600.0
        cost_per_hr = cost / sim_hours if sim_hours > 0 else 0
        results[s] = {
            "total_cost": cost,
            "max_time_s": max_time,
            "sim_hours": sim_hours,
            "cost_per_hour": cost_per_hr
        }
        print(f"{s}: Total Cost = ${cost:,.2f}, Max Time = {max_time}s ({sim_hours:.2f} hrs), Cost/hr = ${cost_per_hr:.2f}/hr")
    else:
        print(f"Report not found for {s}")

with open("cpsat_comparison/hourly_costs.json", "w") as f:
    json.dump(results, f, indent=2)
