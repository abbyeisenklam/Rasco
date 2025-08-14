import argparse
import taskset_parser_gml
from algo import *
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import sys
import concurrent.futures
from ctypes import *
import time
import os
#import cProfile

dna_so_file = "./c_src/libdna_tool.so"   # for running on native linux
dna_dll_file = "./c_src/dna_tool.dll" # for running on native windows

def schedulability_test(all_jobs):
    """Schedulability test.

    Args:
        List of all jobs in one hyperperiod of the task set.

    Returns:
        True if no deadline misses, otherwise false.
    """

    # If job is a sink node of its DAG task check if its finish time <= dag_deadline
    for job in all_jobs:
        if not job.children:
            if job.dag_deadline < job.cur_finish:
                # Unschedulable!
                return False

    return True


def schedulability_baseline_test(all_Utils, all_gammas, all_omegas):
    # Run schedulability check from:
    #  X. Jiang, N. Guan, X. Long, and H. Wan. Decomposition-based real-time scheduling of parallel tasks on multicores platforms. IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems, 39(10):2319–2332, 2020.
    sum_utils = sum(all_Utils)
    max_gamma = max(all_gammas)
    max_omega = max(all_omegas)

    return ( ((1/max_omega) - max_gamma) > 0 ) and ( NUM_CPUS >= ((sum_utils - max_gamma) / ((1/max_omega) - max_gamma) ))


def output_all_jobs_raw(file, all_jobs):
    """Output job info for all jobs in one hyperperiod for the task set.
    
    Args:

    Return:

    """
    for job in all_jobs:
        parents = ', '.join([f"{parent.uid}" for parent in job.parents]) if job.parents else "None"
        file.write(f"Job {job.uid} C: {job.c} BW: {job.bw} (Release: {job.release_offset}, Sub-Deadline: {job.deadline}, Deadline: {job.dag_deadline}) - Parents: {parents}\n")


def output_schedule(file, all_jobs, schedule):
    """Output the static schedule computed by rasco.
    
    Args:
        file: Output file.
        all_jobs: all job objects released in the hyperperiod.
        schedule: List of segment start times and job-budget tuples. Each element has format: (t, job_0.uid, job_0.c, job_0.bw, job_1.uid, job_1.c, job_1.bw, ..., job_NUM_CPUS-1.uid, job_NUM_CPUS-1.c, job_NUM_CPUS-1.bw)

    Return:
        Saves text to file.
    """

    for job in all_jobs:
        file.write(f"{job}\n")

    help_string   = f"STARTING SCHEDULE, format: (t, job_0.uid, job_0.c, job_0.bw, job_1.uid, job_1.c, job_1.bw, ...)\n"
    file.write(help_string)

    for segment in schedule:
        file.write(f"{segment}\n")


def save_to_file(algo_type, all_jobs, schedulable, idx, util, schedule, U_sum, runtime, num_dag_tasks = 0, num_tasks = 0):
    """Saves all job info and schedule to output file.
    
    Args:
        all_jobs: TODO
        schedulable: Boolean for result of schedulability check.
        idx: The index of the task set for the current utilization.
        util: The task set utilization.
        schedule: List of segment start times and job-budget tuples. Each element has format: (t, job_0.uid, job_0.c, job_0.bw, job_1.uid, job_1.c, job_1.bw, ..., job_NUM_CPUS-1.uid, job_NUM_CPUS-1.c, job_NUM_CPUS-1.bw)

    Return:
        Saves to "./output/out_{util}_{idx}.txt".
    """
    print(f"TASKSET IDX: {idx}, UTIL: {util}, SCHEDULABLE: {schedulable}, ACTUAL UTIL: {U_sum}")
    output_string = f"TASKSET IDX: {idx}, UTIL: {util}, SCHEDULABLE: {schedulable}, RUNTIME: {runtime}, NUM TASKGRAPHS: {num_dag_tasks}, NUM TASKS: {num_tasks}\n"

    if algo_type == ALGO_RASCO:
        directory = "./RASCO"
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(f"{directory}/out_{util}_{idx}.txt", "w") as file:
            file.write(output_string)
            output_schedule(file, all_jobs, schedule)
    elif algo_type == ALGO_BASELINE_SIM:
        directory = "./baseline-sim"
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(f"{directory}/out_{util}_{idx}.txt", "w") as file:
            file.write(output_string)
            output_schedule(file, all_jobs, schedule)
    elif algo_type == ALGO_BASELINE_TEST:
        directory = "./baseline-test"
        if not os.path.exists(directory):
            os.makedirs(directory)
        with open(f"{directory}/out_{util}_{idx}.txt", "w") as file:
            file.write(output_string)


def load_dna_data():
    """Load DNA theta data for each workload into global variables all_{workload}_phases"""

    dna_funcs = CDLL(dna_dll_file)
    global dna_funcs_global
    dna_funcs_global = dna_funcs

    # Define the return type and argument types for the function
    get_phase_entries = dna_funcs.get_phase_entries
    get_phase_entries.restype = POINTER(PhaseEntry)
    get_phase_entries.argtypes = [c_size_t, c_size_t, c_int]

    get_theta_entries = dna_funcs.get_theta_entries
    get_theta_entries.restype = POINTER(PhaseEntry)
    get_theta_entries.argtypes = [c_size_t, c_size_t, c_int]

    get_theta_sub_entries = dna_funcs.get_theta_sub_entries
    get_theta_sub_entries.restype = POINTER(PhaseEntry)
    get_theta_sub_entries.argtypes = [c_size_t, c_size_t, c_int, c_size_t]

    # Load phase and theta info for all workloads
    for task_name in range(4):
        for cache in range(1, MAX_CACHE_ITR):
            for membw in range(1, MAX_MEMBW_ITR):
                # Call this function for all cache and membw, it will setup the data strucutres within c library
                # Before doing anything with theta, we need to setup for alll resources
                ret = get_phase_entries(cache, membw, task_name)
                if not bool(ret):
                    print(f"Failed to retrieve phase entries for task type {task_name}.")
                    assert False

        for cache in range(1, MAX_CACHE_ITR):
            for membw in range(1, MAX_MEMBW_ITR):
                # Get theta values, returns pointer to compelte PhaseEntry structure
                entry = get_theta_entries(cache, membw, task_name).contents
                if task_name == 1:
                    all_canneal_phases[cache][membw].append(entry)
                    for i in range(1,entry.num_entries):
                        entry = get_theta_sub_entries(cache, membw, task_name, i).contents
                        all_canneal_phases[cache][membw].append(entry)
                elif task_name == 2:
                    all_fft_phases[cache][membw].append(entry)
                    for i in range(1,entry.num_entries):
                        entry = get_theta_sub_entries(cache, membw, task_name, i).contents
                        all_fft_phases[cache][membw].append(entry)
                elif task_name == 3:
                    all_streamcluster_phases[cache][membw].append(entry)
                    for i in range(1,entry.num_entries):
                        entry = get_theta_sub_entries(cache, membw, task_name, i).contents
                        all_streamcluster_phases[cache][membw].append(entry)
                elif task_name == 0:
                    all_dedup_phases[cache][membw].append(entry)
                    for i in range(1,entry.num_entries):
                        entry = get_theta_sub_entries(cache, membw, task_name, i).contents
                        all_dedup_phases[cache][membw].append(entry)
        print(f"Done loading in phase and theta information for task id {task_name}")


dna_funcs_global = None
def run_rasco(util, idx, args):
    """Single thread executor"""

    print(f"Running for taskset idx: {idx}, util: {util}")

    # Get a list of all subtask objects from the current task set's .gml files
    taskset, U_sum = taskset_parser_gml.parse_taskset(args.taskset_path, util, idx)
    if taskset is None:
        print("FAILED TO GET TASKS")
        sys.exit(0)

    # Calculate the number of dag_tasks and tasks in the task set
    num_dag_tasks = len(taskset)
    num_tasks = sum(len(dag_task) for dag_task in taskset)

    # Run rasco
    start_time = time.time()
    all_jobs, all_Utils, all_gammas, all_omegas, schedule = run_algo(taskset, args.algo_type, idx)
    end_time = time.time()
    runtime = end_time - start_time

    # Schedulability check
    if args.algo_type == ALGO_BASELINE_TEST:
        schedulable = schedulability_baseline_test(all_Utils, all_gammas, all_omegas)
    else:
        schedulable = schedulability_test(all_jobs)
    
    # Save schedule to output file
    save_to_file(args.algo_type, all_jobs, schedulable, idx, util, schedule, U_sum, runtime, num_dag_tasks, num_tasks)


def run_multithreaded_tasksets(args):
    """For running experiment with multiple threads"""

    print("LOADING TASKSETS")

    # Create a list of all (util, idx) combinations to iterate over
    tasksets = [(np.round(util, 1), idx) for util in np.arange(args.min_util, args.max_util + args.min_util, args.min_util) for idx in range(args.max_idx)]

    # Split the work across multiple processes using ProcessPoolExecutor
    with concurrent.futures.ProcessPoolExecutor(max_workers=args.num_threads) as executor:
        futures = [executor.submit(run_rasco, util, idx, args) for util, idx in tasksets]

        # Optional: Wait for all threads to complete
        for future in concurrent.futures.as_completed(futures):
            try:
                future.result()  # To catch any exceptions raised during execution
            except Exception as e:
                print(f"An error occurred: {e}")
                sys.exit(1)


def main():
    '''Run Rasco offline algorithm for all of the task sets in tasket_path.

    Args:
        taskset_path: The path to all of the data-multi-m{NUM_CPUS}-u{taskset_util} folders.
        max_idx: Maximum number of tasksets for each utilization step.
        min_util: Lowest utilization for any taskset.
        max_util: Highest utilization for any taskset.
        num_threads: Number of threads to use for experiment.
        algo_type: 0 for baseline-test, 1 for Rasco, 2 for baseline-sim.

    Return:
        Outputs Schedule for each task set to 'output' directory.
    '''

    # Create the parser
    parser = argparse.ArgumentParser(
        description="rasco offline algorithm for creating schedule + resource allocations for DAG task graphs.")
    
    # Add arguments
    parser.add_argument("taskset_path", type=str, help="Relative path for all tasksets")
    parser.add_argument("max_idx", type=int, help="Maximum number of tasksets within the experiment")
    parser.add_argument("min_util", type=float, help="Lowest utilization within a taskset")
    parser.add_argument("max_util", type=float, help="Highest utilization within a taskset")
    parser.add_argument("num_threads", type=int, help="Number of threads to split the tasksets across")
    parser.add_argument("algo_type", type=int, help="0 for baseline-test, 1 for Rasco, 2 for baseline-sim")
    
    # Parse the command-line arguments
    args = parser.parse_args()

    # Load in theta data for each workload
    load_dna_data()

    # Run Rasco on each task set in the experiment
    if (args.num_threads > 1):
        run_multithreaded_tasksets(args)
    else:
        for util in np.round(np.arange(args.min_util, args.max_util + args.min_util, args.min_util), decimals=1):
            for idx in range(args.max_idx):
                run_rasco(util, idx, args)


if __name__ == "__main__":
    main()