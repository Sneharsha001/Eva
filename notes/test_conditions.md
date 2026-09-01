# Experimental Setup and Conditions

## 1. Instance Types (`src/simulation/config/ec2_config_virt.json`)
The simulation configuration defines instances with the following [GPU, CPU, RAM] capacities and hourly costs:

- **p3 family**:
  - `p3.2xlarge`: Capacity: [1, 8, 61], Cost: $3.06/hr
  - `p3.8xlarge`: Capacity: [4, 32, 244], Cost: $12.24/hr
  - `p3.16xlarge`: Capacity: [8, 64, 488], Cost: $24.48/hr
- **c7i family**:
  - Capacities range from [0, 2, 4] for `c7i.large` up to [0, 192, 384] for `c7i.48xlarge`.
  - Costs range from $0.08925/hr to $8.568/hr.
- **r7i family**:
  - Capacities range from [0, 2, 16] for `r7i.large` up to [0, 192, 1536] for `r7i.48xlarge`.
  - Costs range from $0.1323/hr to $12.7008/hr.

## 2. Workload Trace (`src/pai_trace/traces/pai_200.json`)
- **Task Count**: 200 tasks (indexed "0" to "199")
- **Fields per Task**: 
  - `name`: job name (e.g., "resnet18[0]")
  - `arrival_time`: time of arrival
  - `duration`: duration of the task
  - `init_delay`, `full_throughput`, `total_iters`, `support_throughput_aware`
  - `tasks`: A dictionary of sub-tasks, where each task includes:
    - `demand`: specifies the required resources, e.g., `"any": [1, 12, 16]` for [GPU, CPU, RAM]
    - `shm_size`, `image_id`, `fetch_delay`, `build_image_delay`, `kill_delay`, `upload_delay`

## 3. Experiment Driver (`src/experiment_driver_200.py`)
- **Schedulers Ran**: `NaiveScheduler`, `EVAGangScheduler`, `StratusScheduler`, `OwlScheduler`, `SynergyScheduler`
- **Contention Factor**: 0.95 (`contention_factor = 0.95`)
- **Scheduling Interval**: 300 (`"scheduling_interval": 300`)
- **Results Output Location**: `simulation_experiments/<scheduler>_pai_200/report.json` (where `<scheduler>` is the scheduler class name, and `pai_200` is derived from the trace filename)

## 4. Scheduler Interface (`src/master/scheduler/scheduler.py` & `eva_gang_scheduler.py`)
The scheduler interface for generating planned configurations:
- Base class `Scheduler` in `scheduler.py`: 
  ```python
  def generate_planned_config(jobs, tasks, instances, instance_types, time)
  ```
- Extended class `EVAGangScheduler` in `eva_gang_scheduler.py`:
  ```python
  def generate_planned_config(self, jobs, tasks, instances, instance_types, contention_map, up_instance_ids, unfinished_job_ids, current_config, time, event_occurred, real_reconfig=True)
  ```
