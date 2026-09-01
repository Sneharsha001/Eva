import os
import json

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
    return int(max_time)

def calculate_total_cost_fast(report):
    max_time = get_max_time(report)
    total_cost = 0.0
    for instance_id, instance in report['instances'].items():
        it_id = instance['instance_type_id']
        hourly_rate = report['instance_types'][str(it_id)]['cost']
        for session in instance['active_session_queue']:
            start = session['worker_register_start_time']
            end = session['shut_down_start_time'] if session['shut_down_start_time'] is not None else max_time
            if start <= max_time:
                actual_end = min(end, max_time)
                duration_s = max(0, actual_end - start)
                total_cost += (duration_s / 3600.0) * hourly_rate
    return total_cost, max_time

results = {}
for s in schedulers:
    report_path = os.path.join(base_dir, f"{s}_pai_200", "report.json")
    if os.path.exists(report_path):
        with open(report_path, 'r') as f:
            report = json.load(f)
        cost, max_time = calculate_total_cost_fast(report)
        sim_hours = max_time / 3600.0
        cost_per_hr = cost / sim_hours if sim_hours > 0 else 0
        results[s] = {
            "total_cost": round(cost, 2),
            "max_time_s": max_time,
            "sim_hours": round(sim_hours, 2),
            "cost_per_hour": round(cost_per_hr, 2)
        }
        print(f"{s}: Total Cost = ${cost:,.2f}, Horizon = {max_time:,} s ({sim_hours:.2f} hrs), Cost/hr = ${cost_per_hr:.2f}/hr")

with open("cpsat_comparison/hourly_costs.json", "w") as f:
    json.dump(results, f, indent=2)
