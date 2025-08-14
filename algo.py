import sys
import matplotlib.pyplot as plt # type: ignore
import networkx as nx # type: ignore
from networkx.drawing.nx_agraph import graphviz_layout # type: ignore
from rasco_subfunctions import *


verbose_rasco = False
def run_algo(taskset, algo_type, taskset_idx):
    '''Rasco pre-processing and main algorithm.

    Args:  
        taskset: A list of all DAG tasks in the task set, each DAG task is a list of Subtask objects
        algo_type: ALGO_BASELINE_TEST, ALGO_RASCO, or ALGO_BASELINE_SIM
        taskset_idx: Index of current task set.

    Return: 
        all_jobs: List of all Job objects in the hyperperiod
        all_Utils: For baseline-test schedulability test.
        all_gammas: For baseline-test schedulability test.
        all_omegas: For baseline-test schedulability test.
        schedule: List of segment start times and job-budget tuples. Each element has format: (t, job_0.uid, job_0.c, job_0.bw, job_1.uid, job_1.c, job_1.bw, ..., job_NUM_CPUS-1.uid, job_NUM_CPUS-1.c, job_NUM_CPUS-1.bw)
    '''

    # =============================== RASCO PREPROCESSING =============================== #

    all_Utils  = [] # For baseline-test schedulability check
    all_gammas = [] # For baseline-test schedulability check
    all_omegas = [] # For baseline-test schedulability check
    all_Utils, all_gammas, all_omegas = rasco_preprocess(taskset, algo_type)
    
    #  ============================== INITIALIZE RASCO VARS ==============================  #

    schedule = [] # Output of Rasco

    # Get all job instances in the hyperperiod (returns a list of job objects) and the set of all anchor points (DAG task releases)
    all_jobs, anchor_points = get_all_jobs(taskset)

    # Get t
    t = 0

    # Get set of ready tasks (Q), jobs are initially ordered by release offsets, so break as soon as one is larger than 0
    ready_set = []
    for job in all_jobs:
        if job.release_offset == 0:
            ready_set.append(job)
        else:
            break
    
    # Get tnext (either an anchor point or the next earliest job completion)
    tnext = get_tnext(ready_set, anchor_points, t)

    # =================== RETURN IMMEDIATELY FOR BASELINE SCHED TEST ==================== #
   
    if algo_type == ALGO_BASELINE_TEST:
        return all_jobs, all_Utils, all_gammas, all_omegas, None

    # =========================== BEGIN RASCO OUTER WHILE LOOP ============================ #

    while (True):

        # Save initial deadline, assign base budgets
        for job in ready_set:
            job.deadline_init = job.deadline
            job.c = job.c_init
            job.bw = job.bw_init

        # Calculate sched_set (the set of NUM_CPUS jobs with earliest deadlines) and the total resource budget used by sched_set
        ready_set = sorted(ready_set, key=lambda job: job.deadline)
        sched_set = ready_set[:NUM_CPUS]
        res_sched = {'c': sum([job.c for job in sched_set]), 'bw': sum([job.bw for job in sched_set])}

        # Get tnext
        tnext = get_tnext(sched_set, anchor_points, t)

        if verbose_rasco:
            print("Sched set:")
            for job in sched_set:
                print(f"\t{job}")
            print(f"Resources used: ({res_sched.get('c')}, {res_sched.get('bw')})")
            

        # =========================== INNER RESOURCE ALLOCATION WHILE LOOP ============================ #

        if algo_type != ALGO_BASELINE_SIM:

            # Check if initial budgets exceed the maximum partitions, if so, take away resources from the jobs with largest slack
            sched_set, res_sched = check_if_overallocated(sched_set, res_sched, t, tnext)
            
            # Recalc tnext
            tnext = get_tnext(sched_set, anchor_points, t)
            # Update completion times
            for job in ready_set:
                job.cur_finish = int(calc_task_finish(job, t, tnext))

            if verbose_rasco:
                print("Sched set after taking away resources:")
                for job in sched_set:
                    print(f"\t{job}")
                print(f"Running res alloc... resources used: ({res_sched.get('c')}, {res_sched.get('bw')})")

            while (True):

                if verbose_rasco:
                    print(f"Resources used: ({res_sched.get('c')}, {res_sched.get('bw')})")

                # Select job to get additional resources (c=1 or bw=1)
                chosen_job, c, bw = allocate_resource(ready_set, sched_set, res_sched, tnext - t)

                if verbose_rasco:
                    print(f"Job chosen by res alloc: {chosen_job}")
                    print(f"Resource chosen by res alloc: ({c}, {bw})")

                # No more resources could be given out, segment complete, break out of the inner loop
                if chosen_job is None:
                    break

                # Else give the additional resources to the job and update params
                chosen_job.c += c
                chosen_job.bw += bw
                new_finish_time = int(calc_task_finish(chosen_job, t, tnext))
                chosen_job.deadline = chosen_job.deadline - (chosen_job.cur_finish - new_finish_time) if chosen_job.cur_finish < new_finish_time else chosen_job.deadline
                chosen_job.cur_finish = int(calc_task_finish(chosen_job, t, tnext))

                # Check if we should swap this job into sched
                if not is_in_set(sched_set, chosen_job):
                    if verbose_rasco:
                        print("Chosen job was not in sched set")
                    max_deadline_job = sched_set[-1]
                    if (chosen_job.deadline < max_deadline_job.deadline) and (res_sched.get('c') - max_deadline_job.c + chosen_job.c <= MAX_CACHE_ITR) and (res_sched.get('bw') - max_deadline_job.bw + chosen_job.bw <= MAX_MEMBW_ITR):
                        if verbose_rasco:
                            print("Chosen job was swapped into sched set")
                        sched_set.remove(max_deadline_job)
                        sched_set.append(chosen_job)
                        sched_set = sorted(sched_set, key=lambda job: job.deadline)

                if is_in_set(sched_set, chosen_job):
                    if verbose_rasco:
                        print("Chosen job is in sched set")
                    # Update total budget used
                    res_sched = {'c': sum([job.c for job in sched_set]), 'bw': sum([job.bw for job in sched_set])}

                    tnext = get_tnext(sched_set, anchor_points, t)

                    # Update completion times
                    for job in ready_set:
                        job.cur_finish = int(calc_task_finish(job, t, tnext))
        
        if verbose_rasco:
            print("Sched set is finalized:")
            for job in sched_set:
                print(f"\t{job}")

        # If we are in baseline simulation mode, skip these checks
        if algo_type == ALGO_RASCO:
            assert res_sched.get('c') == MAX_CACHE_ITR and res_sched.get('bw') == MAX_MEMBW_ITR

        # sched_set is finalized (broke out of inner resource alloc loop), reset any unscheduled jobs
        for job in ready_set:
            if not is_in_set(sched_set, job):
                job.c = job.c_init
                job.bw = job.bw_init
                job.deadline = job.deadline_init
                if algo_type == ALGO_BASELINE_SIM:
                    job.cur_finish = tnext + int((job.max_insn - job.cur_insn) / job.even_rate)
                else:
                    job.cur_finish = int(calc_task_finish(job, tnext, sys.maxsize))

        # Update jobs that WERE scheduled
        for job in sched_set:
            if job.cur_finish <= tnext: # Job finished
                job.cur_finish = tnext
                job.complete = True
                job.cur_insn = job.max_insn
                ready_set.remove(job)

                if verbose_rasco:
                    print(f"Job finished: {job}")

                # Check if any successors can be released and add them to ready_set
                ready_jobs = release_successors(job, algo_type)
                ready_set.extend(ready_jobs)

            else:
                if algo_type == ALGO_BASELINE_SIM:
                    insns_retired = min(job.max_insn - job.cur_insn, int((tnext - t) * job.even_rate))
                else:
                    cur_phase, phase_idx = find_phase(job, job.cur_insn, job.c, job.bw)
                    insns_retired = calc_insn_in_range(job, job.cur_insn, cur_phase, phase_idx, tnext - t, job.c, job.bw)
                job.cur_insn += insns_retired

                # Check again if job finished, incase rounding difference between time vs. instructions
                if job.cur_insn >= job.max_insn:
                    job.cur_finish = tnext
                    job.complete = True
                    job.cur_insn = job.max_insn
                    ready_set.remove(job)

                    if verbose_rasco:
                        print(f"Job finished: {job}")

                    # Check if any successors can be released and add them to ready_set
                    ready_jobs = release_successors(job, algo_type)
                    ready_set.extend(ready_jobs)

        # Sort sched_set based on previous segment to mitigate core migrations
        if schedule == []:
            while len(sched_set) < NUM_CPUS:
                sched_set.append(None)
        else:
            prev_sched_job_uids = [schedule[-1][i] for i in range(1, len(schedule[-1]), 3)]
            sched_set = reorder_jobs(prev_sched_job_uids, sched_set)
        
        # Save jobs in sched_set with their resource allocation for the current segment
        choice = (t,)
        for job in sched_set:
            if job is None:
                    choice += (None, 0, 0)
            else:
                choice += (job.uid, job.c, job.bw)

        schedule.append(choice)

        # Check if done
        if all([job.complete for job in all_jobs]):
            break

        # Otherwise, prepare for next segment, update decision points
        if not ready_set:
            t = min([anchor_point for anchor_point in anchor_points if anchor_point > t])
        else:
            t = tnext

        # Add newly released source jobs to Q
        for job in all_jobs:
            if (job.release_offset == t) and (not job.parents):
                ready_set.append(job)

    return all_jobs, all_Utils, all_gammas, all_omegas, schedule