"""
eva_cpsat_scheduler.py
======================
Wrapper scheduler that invokes EVAGangScheduler as baseline and applies
CP-SAT refinement to the planned configuration.

Design Principles:
1. Strict Preservational Fallback:
   EVAGangScheduler generates the initial planned_config and maintains all internal
   accounting (reconfig history, event interarrival times, delays).
2. CP-SAT Refinement:
   If enabled, CP-SAT searches for an assignment that yields strictly higher net savings
   under the same TNRP contention penalties, resource constraints, and migration costs.
3. Fail-Safe Guarantee:
   If CP-SAT fails, times out, is infeasible, or returns a non-improving plan,
   the original EVAGangScheduler plan is preserved unchanged.
4. Comprehensive Observability:
   Every refinement invocation records simulation time, candidate task count,
   baseline Eva savings, CP-SAT savings, objective delta, solver status, and solve time.
   These are tracked in get_report() and optionally persisted to refinement_log.json.
"""

import copy
import json
import logging
import os
import time as time_module
import numpy as np

from .eva_gang_scheduler import EVAGangScheduler
from .cpsat_refiner import refine_with_cpsat

logger = logging.getLogger(__name__)


class EVACPSATScheduler(EVAGangScheduler):
    def __init__(self,
                 enable_cpsat: bool = False,
                 time_limit_sec: float = 5.0,
                 refinement_log_path: str = None,
                 default_contention_rate: float = 0.95):
        super().__init__(default_contention_rate=default_contention_rate)
        self.enable_cpsat = enable_cpsat
        self.time_limit_sec = time_limit_sec
        self.refinement_log_path = refinement_log_path
        self.refinement_history = []

    def get_report(self):
        report = super().get_report()
        report["enable_cpsat"] = self.enable_cpsat
        report["time_limit_sec"] = self.time_limit_sec
        report["refinement_history"] = self.refinement_history
        return report

    def _persist_refinement_log(self):
        if not self.refinement_log_path:
            return
        try:
            parent_dir = os.path.dirname(os.path.abspath(self.refinement_log_path))
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            with open(self.refinement_log_path, "w") as f:
                json.dump(self.refinement_history, f, indent=2)
        except Exception as e:
            self._logger.error(f"Failed to persist refinement log to {self.refinement_log_path}: {e}")

    def generate_planned_config(self,
                                jobs,
                                tasks,
                                instances,
                                instance_types,
                                contention_map,
                                up_instance_ids,
                                unfinished_job_ids,
                                current_config,
                                time,
                                event_occurred,
                                real_reconfig=True):
        # 1. Run baseline EVAGangScheduler
        eva_planned_config = super().generate_planned_config(
            jobs=jobs,
            tasks=tasks,
            instances=instances,
            instance_types=instance_types,
            contention_map=contention_map,
            up_instance_ids=up_instance_ids,
            unfinished_job_ids=unfinished_job_ids,
            current_config=current_config,
            time=time,
            event_occurred=event_occurred,
            real_reconfig=real_reconfig
        )

        # Only refine during real reconfiguration events when CP-SAT is enabled
        if not real_reconfig or not self.enable_cpsat:
            return eva_planned_config

        # 2. Extract context for refinement
        try:
            assignable_instances = {
                iid: instances[iid]
                for iid in self._get_assignable_instance_ids(instances, up_instance_ids)
            }
            reconfigurable_job_ids = self._get_reconfigurable_job_ids(jobs, unfinished_job_ids)
            candidate_task_ids = [
                tid for jid in reconfigurable_job_ids for tid in jobs[jid].task_ids
            ]

            if len(candidate_task_ids) == 0:
                return eva_planned_config

            fixed_config = self._create_initial_config(jobs, tasks, instances, unfinished_job_ids)
            active_current_config = {
                iid: tids for iid, tids in current_config.items() if len(tids) > 0
            }

            all_unfinished_tasks = [
                tid for jid in unfinished_job_ids for tid in jobs[jid].task_ids
            ]
            task_to_min_it_map = self.get_min_instance_type(
                all_unfinished_tasks, tasks, instance_types
            )

            # Compute mean_time_to_next_reconfig matching Eva's exact formula
            avg_interarrival = self.get_average_event_interarrival_time()
            if avg_interarrival is None or np.isnan(avg_interarrival) or avg_interarrival <= 0:
                mean_time_to_next_reconfig = time
            else:
                lamb = 1.0 / avg_interarrival
                num_of_events = len(self.event_arrival_times)
                prob_of_reconfig = len(self.global_reconfig_history) / max(1, num_of_events)
                if prob_of_reconfig <= 0:
                    mean_time_to_next_reconfig = time
                elif prob_of_reconfig >= 1.0:
                    mean_time_to_next_reconfig = time
                else:
                    mean_time_to_next_reconfig = -1.0 / (lamb * np.log(1.0 - prob_of_reconfig))

            # 3. Invoke CP-SAT refiner
            refined_config, log_entry = refine_with_cpsat(
                eva_planned_config=eva_planned_config,
                current_config=active_current_config,
                candidate_task_ids=candidate_task_ids,
                fixed_config=fixed_config,
                tasks=tasks,
                jobs=jobs,
                instances=assignable_instances,
                instance_types=instance_types,
                task_to_min_it_map=task_to_min_it_map,
                contention_map=contention_map,
                horizon_T=mean_time_to_next_reconfig,
                sim_time=time,
                time_limit_sec=self.time_limit_sec,
                default_contention_rate=self.default_contention_rate,
                next_pseudo_id_start=self._next_instance_id - 500
            )

            # 4. Fallback verification
            if log_entry.get("plan_selected") == "CPSAT":
                try:
                    self._check_config_feasibility(refined_config, instances, instance_types, tasks)
                    final_plan = refined_config
                    self._logger.info(
                        f"[EVACPSATScheduler @ {time}s] CP-SAT improved objective by "
                        f"{log_entry.get('objective_improvement')}. Adopting refined plan."
                    )
                except Exception as val_err:
                    self._logger.warning(
                        f"[EVACPSATScheduler @ {time}s] CP-SAT plan failed feasibility check: {val_err}. "
                        f"Falling back to Eva plan."
                    )
                    final_plan = eva_planned_config
                    log_entry["plan_selected"] = "EVA"
                    log_entry["notes"].append(f"Feasibility exception: {val_err}")
            else:
                final_plan = eva_planned_config

            self.refinement_history.append(log_entry)
            self._persist_refinement_log()
            return final_plan

        except Exception as e:
            self._logger.error(
                f"[EVACPSATScheduler @ {time}s] Exception during refinement: {e}. "
                f"Falling back to original Eva plan.",
                exc_info=True
            )
            fallback_log = {
                "sim_time": time,
                "solver_status": f"EXCEPTION_{type(e).__name__}",
                "plan_selected": "EVA",
                "notes": [str(e)]
            }
            self.refinement_history.append(fallback_log)
            self._persist_refinement_log()
            return eva_planned_config
