import copy
import sys
from ctypes import *
from config import *
from hyper_period import compute_hyper_period
from config import *

#  ============================== TASK PHASE ARRAYS ==============================  #

all_canneal_phases   = [[[] for _ in range(MAX_MEMBW_ITR)] for _ in range(MAX_CACHE_ITR)]
all_streamcluster_phases = [[[] for _ in range(MAX_MEMBW_ITR)] for _ in range(MAX_CACHE_ITR)]
all_fft_phases       = [[[] for _ in range(MAX_MEMBW_ITR)] for _ in range(MAX_CACHE_ITR)]
all_dedup_phases       = [[[] for _ in range(MAX_MEMBW_ITR)] for _ in range(MAX_CACHE_ITR)]

#  ============================== RASCO CLASSES ==============================  #

class Subtask:
    '''Subtask object constructor. Note that:  
        1. The 'parents' and 'children' fields must be initialized outside the constructor, since they contain pointers to other subtask objects.
        2. All time-related variables are in nanoseconds.
        4. The 'release_offset', 'deadline', 'dag_deadline', and 'cur_finish' are relative (to the subtask release time = 0). They are set in preprocessing, so they are initialized to 0 for now.
        5. We are assuming implicit deadlines (relative deadline = period).

    Args:
        data: A dictionary of subtask info.

    Returns:
        A subtask object.
    '''

    def __init__(self, data):
        try:
            self.name           = data['name']
            self.uid            = data['uid']
            self.period         = data['p']
            self.wcets          = data['wcets'] # large double array, indexed by c and bw
            self.max_insn       = data['max_insn']
            self.even_rate      = self.max_insn / self.wcets[int((MAX_CACHE_ITR) / NUM_CPUS)][int((MAX_MEMBW_ITR)/ NUM_CPUS)]
            self.children       = [] # set at task-graph construction so they can be pointers to other subtask objects
            self.parents        = [] # set at task-graph construction so they can be pointers to other subtask objects
            self.c_init         = 2 # min resource partition set to 2
            self.bw_init        = 2

            # Everything below needs to be offset by the job release''s anchor point when we create job instances
            self.release_offset = 0 # set depending on pre-processing method 
            self.deadline       = 0 # set depending on pre-processing method 
            self.cur_finish     = 0 # set depending on pre-processing method 
            self.dag_deadline   = int(self.period) # the relative deadline of the DAG task that this subtask is part of

        except KeyError as e:
            print(f"Missing key: {e}")

    def get_phase_ref(self):
        if self.name == "canneal":
            return all_canneal_phases
        elif self.name == "streamcluster":
            return all_streamcluster_phases
        elif self.name == "fft":
            return all_fft_phases
        elif self.name == "dedup":
            return all_dedup_phases
        else:
            print(f"Don't yet have a global all_{self.name}_phases")
            assert False

    @staticmethod
    def calculate_max_deadline(parents):
        """Recursively calculate the maximum deadline of all parents and their ancestors.

        Args:
            parents: A list of parent Subtask objects.

        Return:
            The maximum deadline among all parents and their ancestors.
        """

        max_deadline = 0
        for parent in parents:
            parent_max_deadline = parent.deadline
            if parent.parents:
                parent_max_deadline = max(parent_max_deadline, Subtask.calculate_max_deadline(parent.parents))
            max_deadline = max(max_deadline, parent_max_deadline)
        return max_deadline

    def __repr__(self):
        parent_uids = ', '.join([str(parent.uid) for parent in self.parents]) if self.parents else "None"
        children_uids = ', '.join([str(child.uid) for child in self.children]) if self.children else "None"
        return f"Subtask(uid={self.uid}, name={self.name}, parent_uids=[{parent_uids}], child_uids[{children_uids}], period={str(self.period)})"


class Job(Subtask):
    """Job object constructor. A Job is an instance of a Subtask. Note that:  
        1. The 'parents' and 'children' fields must be initialized outside the constructor, since they contain pointers to other job objects.
        2. All time-related variables are in nanoseconds.
        4. The 'release_offset', 'deadline', 'dag_deadline', and 'cur_finish' are absolute (relative to the start of the hyperperiod at t=0). They are set in preprocessing, so they are initialized to 0 for now.
        5. We are assuming implicit deadlines (relative deadline = period).
    
    Args:
        Subtask: the Subtask object that this job is an instance of.
        release_num: The release number of the DAG task in the hyperperiod.
        anchor_point: The release offset of the release num.
        
    Returns:
        A Job object.
    """

    def __init__(self, subtask, release_num, anchor_point):
        # Copy all attributes from the subtask
        self.__dict__.update(subtask.__dict__)
        
        # Store the original subtask reference
        self.subtask = subtask

        # Need to re-initialize parent and child pointers (want them to point to job objects not subtask objects)
        self.parents = []
        self.children = []
        
        # Add job-specific attributes
        self.release_num = int(release_num)
        self.anchor_point = int(anchor_point)
        self.is_anchor_point = 0 # Set to true if this job is a source node (i.e., it has no parents)

        # Update job info to be in absolute time (i.e., relative to start of hyperperiod t=0)
        self.release_offset = self.release_offset + self.anchor_point
        self.deadline = self.deadline + self.anchor_point
        self.cur_finish = self.cur_finish + self.anchor_point
        self.dag_deadline = self.dag_deadline + self.anchor_point
        
        # Initialize job state variables
        self.c = self.c_init
        self.bw = self.bw_init
        self.deadline_init = self.deadline
        self.complete = False
        self.cur_insn = 1
        
    def __repr__(self):
        # Handle both object references and string IDs in parents and children lists
        
        parent_uids = []
        for parent in self.parents if self.parents else []:
            parent_uids.append(str(parent.uid))
        
        children_uids = []
        for child in self.children if self.children else []:
            children_uids.append(str(child.uid))
                
        parent_uids_str = ', '.join(parent_uids) if parent_uids else "None"
        children_uids_str = ', '.join(children_uids) if children_uids else "None"
        
        return f"Job(uid={self.uid}, name={self.name}, parent_uids=[{parent_uids_str}], child_uids[{children_uids_str}], is_anchor_point={self.is_anchor_point} release_time={self.release_offset}, deadline={self.deadline}, dag_deadline={self.dag_deadline}, cur_finish={self.cur_finish}, complete={self.complete}, c={self.c}, bw={self.bw})"


class ThetaT(Structure):
    """Define the ThetaT structure. From R. Gifford, N. Gandhi, L. T. X. Phan, and A. Haeberlen. DNA: Dynamic resource allocation for soft real-time multicore systems. In RTAS, 2021."""

    _fields_ = [
        ("value", c_long),
        ("which", c_int8)  # -1, 0, or 1 as integers
    ]

    def __str__(self):
        return f"ThetaT(value={self.value}, which={self.which})"



class PhaseEntry(Structure):
    "Define the phase_entry_t structure. From R. Gifford, N. Gandhi, L. T. X. Phan, and A. Haeberlen. DNA: Dynamic resource allocation for soft real-time multicore systems. In RTAS, 2021."

    # Create the two-dimensional array type for theta_set
    _theta_array_type = ThetaT * MAX_MEMBW_ITR
    _theta_set_type = _theta_array_type * MAX_CACHE_ITR

    _fields_ = [
        ("task_id", c_uint),
        ("phase_idx", c_uint),
        ("cache", c_uint),
        ("membw", c_uint),
        ("insn_start", c_ulonglong),
        ("insn_end", c_ulonglong),
        ("insn_rate", c_ulonglong),  # STORED IN S!!!!
        ("num_entries", c_ulonglong),
        ("theta_set", _theta_set_type),  # 2D array of theta_t
        ("next_entry", POINTER("PhaseEntry"))  # Pointer to the next phase_entry_t
    ]

    def __str__(self):
        # Format each theta_set element to align the output in columns
        theta_set_str = "\n".join(
            [" | ".join(f"{self.theta_set[i][j].value:5d},{self.theta_set[i][j].which:2d}" for j in range(MAX_MEMBW_ITR))
             for i in range(MAX_CACHE_ITR)]
        )

        return (
            f"PhaseEntry(task_id={self.task_id}, phase_idx={self.phase_idx}, cache={self.cache}, membw={self.membw}, "
            f"insn_start={self.insn_start}, insn_end={self.insn_end}, insn_rate={self.insn_rate} insns/s)\n"
            #f"theta_set=\n{theta_set_str})"
        )
# Now we replace the forward reference to PhaseEntry
PhaseEntry._fields_[-1] = ("next_entry", POINTER(PhaseEntry))

#  ============================= PREPROCESSING FUNCTIONS =============================  #

def task_is_in_copy_list(target_task, list):
    for task in list:
        if task.uid == target_task.uid:
            return True
        
    return False

def compute_segment_times(dag_task):
    """Used to compute segments for the deadline decomposition method in preprocessing stage.
    
    Args:
        dag_task: List of Subtask objects.
        
    Returns:
        List of segment times.
    """

    # DAG task is originally sorted by release offsets, USE DEADLINES HERE, for preprocess only
    sort_by_deadlines = sorted(copy.copy(dag_task), key=lambda subtask: subtask.deadline)
    deadline_idx = 0
    release_idx = 0
    segments = []
    while deadline_idx < len(sort_by_deadlines) and release_idx < len(dag_task):
        if sort_by_deadlines[deadline_idx].deadline < dag_task[release_idx].release_offset:
            segments.append(sort_by_deadlines[deadline_idx].deadline)
            deadline_idx += 1
        else:
            segments.append(dag_task[release_idx].release_offset)
            release_idx += 1

    # copy over any stragglers
    while deadline_idx < len(sort_by_deadlines):
        segments.append(sort_by_deadlines[deadline_idx].deadline)
        deadline_idx += 1
    while release_idx  < len(dag_task):
        segments.append(dag_task[release_idx].release_offset)
        release_idx += 1

    # quick trick to remove duplicates
    segments = list(dict.fromkeys(segments))

    return segments


verbose_res_select = False
def select_least_impactful_res_under_wcet_constraint(task, compare_time):
    """Returns the resource that causes the smallest increase in wcet, or all 0 if taking away a resource causes the execution time to exceed compare_time.
    
    Args:
        task: The subtask object.
        compare_time: The time to compare against.
    
    Returns:
        (c, bw): one of the values will be 1 the other 0, or they will both be 0 if execution time exceeds compare_time
    """

    if verbose_res_select:
        print(f"select_least_impactful_res for task {task.uid}, c: {task.c_init} bw: {task.bw_init}, compare_time: {compare_time}")

    cache_wcet = float("inf")
    membw_wcet = float("inf")

    if task.c_init == 2 and task.bw_init == 2:
        return 0, 0
    
    # general case
    if task.c_init > 2:
        cache_wcet = task.wcets[task.c_init-1][task.bw_init]
    if task.bw_init > 2:
        membw_wcet = task.wcets[task.c_init][task.bw_init-1]

    # ending case
    if cache_wcet >= compare_time and membw_wcet >= compare_time:
        return 0, 0
    elif cache_wcet >= compare_time:
        return 0, 1
    elif membw_wcet >= compare_time:
        return 1, 0

    # do we just not have enough of one res? 
    if task.c_init == 2:
        return 0, 1
    elif task.bw_init == 2:
        return 1, 0
    
    # otherwise, we can take from either, take the smallest impact
    if cache_wcet <= membw_wcet:
        return 1, 0
    else:
        return 0, 1  


verbose_preprocess = False
def rasco_preprocess(taskset, algo_type):
    """Use the deadline decomposition method from 'Decomposition-based real-time scheduling of parallel tasks on multicore platforms' to set subtask deadlines.

    Args:
        taskset: List of all DAG tasks in the taskset, each DAG task is a list of subtask objects.
        algo_type: Either ALGO_RASCO, ALGO_BASELINE_TEST, or ALGO_BASELINE_SIM.

    Returns:
        all_Utils, all_gammas, all_omegas: Variables needed for the baseline schedulability test.
    """

    class Segment:
        def __init__(self, uid, start, end, fully_contained_tasks):
            self.uid = uid  # integer
            self.start = start  # float
            self.end = end  # float

            # Reference the input lists, no deep copy.
            self.fully_contained_tasks     = fully_contained_tasks  # list of pointers to Subtask objects
            self.partially_contained_tasks = []                   # list of pointers to Subtask objects

            self.is_heavy = False
            self.sum_wcet  = 0.0
            self.threshold = 0.0

        def length(self):
            return self.end - self.start

        def __str__(self):
            """
            Returns a string representation of the Segment's variables
            """
            return (
                f"Segment(uid={self.uid}, start={self.start}, end={self.end}, "
                f"fully_contained_tasks={self.fully_contained_tasks}, "
                f"partially_contained_tasks={self.partially_contained_tasks}, "
                f"is_heavy={self.is_heavy}, threshold={self.threshold})"
            )

    # for schedulability check, need to store one per task graph
    all_omegas = []
    all_gammas = []
    all_Utils  = []

    # For each dag_task:
    for dag_task in taskset:
        not_contained_tasks = copy.copy(dag_task)
        sorted(not_contained_tasks, key=lambda task: task.deadline)
        if verbose_preprocess:
            print("DAG task:")
            #print_DAG(dag_task)
            #draw_DAG(task_graph, "Task Graph")

        dag_task.sort(key=lambda t: t.uid)

        # 1. Assign max resources
        for subtask in dag_task:
            if algo_type != ALGO_RASCO:
                # Assume even partitions for baseline
                subtask.c_init  = int((MAX_CACHE_ITR) / NUM_CPUS)
                subtask.bw_init = int((MAX_MEMBW_ITR) / NUM_CPUS)
            else:
                # Start with max resources for deadline-aware (min resource per core is 2)
                subtask.c_init      = MAX_CACHE_ITR - 2*(NUM_CPUS-1)
                subtask.bw_init     = MAX_MEMBW_ITR - 2*(NUM_CPUS-1)
            
            # Set initial release offsets and finish times using the above resource allocations
            if not subtask.parents:
                subtask.release_offset = 0
            else:
                subtask.release_offset = int(max(parent.cur_finish for parent in subtask.parents))
            subtask.cur_finish = int(subtask.release_offset + subtask.wcets[subtask.c_init][subtask.bw_init])

        # Now we can set deadlines since release_times are set
        for subtask in dag_task:
            if not subtask.children:
                subtask.deadline = subtask.cur_finish
            else:
                subtask.deadline   = int(min(child.release_offset for child in subtask.children))
            
        for subtask in dag_task:
            assert subtask.deadline - subtask.release_offset >= subtask.wcets[subtask.c_init][subtask.bw_init]

        if verbose_preprocess:
            print("After assigning max res...")
            #print_DAG(dag_task)

        # 2. Calc segments and set of tasks that fall competely in each segment
        segment_times = compute_segment_times(dag_task)
        if verbose_preprocess:
            print("all segment_times:")
            print(segment_times)

        # Construct segment objects from segments_times
        segments = []
        i = 0
        for i in range(len(segment_times)):
            if i == len(segment_times)-1:
                break

            start = segment_times[i]
            end   = segment_times[i+1]
            segment = Segment(i, start, end, [])
            if verbose_preprocess:
                print("New segment:")
                print(segment)
            segments.append(segment)

            # Find tasks that fall within the segment range completely
            for subtask in dag_task:
                if subtask.release_offset >= start and subtask.deadline <= end:
                    if verbose_preprocess:
                        print(f"Add task {subtask.uid} to fully contained set")
                    segment.fully_contained_tasks.append(subtask)
                    not_contained_tasks.remove(subtask)

            # Calculate the segment's threshold
            segment.sum_wcet  = 0
            segment.threshold = 0
            for subtask in segment.fully_contained_tasks:
                segment.sum_wcet += int(subtask.wcets[subtask.c_init][subtask.bw_init])
            segment.threshold = segment.sum_wcet / segment.length()

        # Step 3. Calculate total threshold for this task_graph
        total_len = segment_times[-1] - segment_times[0]
        if verbose_preprocess:
            print(f"total length: {total_len}")
        assert total_len > 0, "WOAH TOTAL LEN IS <= 0?!"
        total_threshold = 0
        for subtask in dag_task:
            # tasks not fully contained don't contribute to total threshold
            if subtask in not_contained_tasks:
                continue
            if verbose_preprocess:
                print(f"adding task {subtask.uid} to total_threshold")
            total_threshold += int(subtask.wcets[subtask.c_init][subtask.bw_init])
        total_threshold = total_threshold / total_len
        assert total_threshold > 0, "WOAH TOTAL THRESHOLD IS <= 0"
        if verbose_preprocess:
            print(f"total_len: {total_len}, total_threshold: {total_threshold}")

        # Step 4. for each segment, update if light or heavy        
        for segment in segments:
            segment.is_heavy = segment.threshold > total_threshold

        # Step 5 / 6. Handle all tasks that are not in a single segment, and update heavy
        for segment in segments:
            # Skip over heavy segments for now
            if segment.is_heavy == True:
                if verbose_preprocess:
                    print(f"segment {segment.uid} is heavy, skipping")
                continue
            if verbose_preprocess:
                print(f"segment {segment.uid} is light, processing")

            idx = 0
            while len(not_contained_tasks) > 0:
                subtask = not_contained_tasks[idx]
                if verbose_preprocess:
                    print(f"\ttask {subtask.uid} is NOT fully contined, processing")
                # Is any part of it in the segment?
                if (subtask.release_offset <= segment.start and subtask.deadline >= segment.end):
                    if verbose_preprocess:
                        print(f"\ttask {subtask.uid} falls within the segment {segment.uid}")

                    if ((subtask.wcets[subtask.c_init][subtask.bw_init] + segment.sum_wcet) / segment.length()) < total_threshold:
                        if verbose_preprocess:
                            print(f"\t\ttask {subtask.uid} WCET falls completely within the segment {segment.uid}")
                        segment.fully_contained_tasks.append(subtask)
                        segment.sum_wcet += int(subtask.wcets[subtask.c_init][subtask.bw_init])
                        segment.threshold = segment.sum_wcet / segment.length()
                        segment.is_heavy = segment.threshold > total_threshold
                        assert segment.is_heavy == False, "WOAH, SHOULD NEVER BE HEAVY HERE"
                        not_contained_tasks.remove(subtask)

                    else:
                        # We need to SPLIT task, so part of its execution goes in this segment
                        if verbose_preprocess:
                            print(f"\t\ttask {subtask.uid} WCET falls partially within the segment {segment.uid}")
                        wcet_for_this_seg = min(segment.length(), int((total_threshold * segment.length()) - segment.sum_wcet))
                        if verbose_preprocess:
                            print(f"\t\t\twcet_for_this_seg: {wcet_for_this_seg}, total_threshold: {total_threshold}, segment length: {segment.length()}, segment sum_wcet: {segment.sum_wcet}")
                        assert wcet_for_this_seg >= 0 and wcet_for_this_seg <= segment.length(), "WOAH, WCET_FOR_THIS_SEG ISN'T IN BOUNDS"
                        segment.sum_wcet += int(wcet_for_this_seg)
                        segment.threshold = segment.sum_wcet / segment.length()
                        segment.is_heavy = segment.threshold > total_threshold
                        if wcet_for_this_seg > 0:
                            segment.partially_contained_tasks.append(subtask)

                        # now remove subtask from not_contained_tasks, insert new Task with remaining params
                        not_contained_tasks.remove(subtask)
                        tmp = copy.deepcopy(subtask)
                        assert wcet_for_this_seg <= segment.length()
                        tmp.wcets[tmp.c_init][tmp.bw_init] -= int(wcet_for_this_seg)
                        if tmp.wcets[tmp.c_init][tmp.bw_init] < 0:
                            print(f"WOAH, UPDATED WCET IS < 0?! : {tmp.wcets[tmp.c_init][tmp.bw_init]}")
                            assert False
                        not_contained_tasks.insert(0, tmp)
                        # go onto the next segment
                        break
                
                idx += 1 
                if idx >= len(not_contained_tasks):
                    break
        
        # After both loops, check if not_contained_tasks still has tasks in it
        if len(not_contained_tasks) > 0:
            if verbose_preprocess:
                print(f"not_contained_tasks still has some tasks to process, ADD TO HEAVY SEGMENTS")
                for subtask in not_contained_tasks:
                    print(f"\ttask {subtask.uid} is still not contained")
                

            while len(not_contained_tasks) > 0:
                subtask = not_contained_tasks[0]
                not_contained_tasks.remove(subtask) # will be added back in later if needed
                tmp = copy.deepcopy(subtask)
                task_done = False
                if verbose_preprocess:
                    print(f"PROCESSING TASK {tmp.uid}")
                for segment in segments:
                    if (tmp.release_offset <= segment.start and tmp.deadline >= segment.end):
                        if verbose_preprocess:
                            print(f"\tFalls within segment {segment.uid}")
                        if tmp.wcets[tmp.c_init][tmp.bw_init] <= segment.length():
                            if verbose_preprocess:
                                print(f"\t\tremaining wcet {tmp.wcets[tmp.c_init][tmp.bw_init]} <= seg len {segment.length()}")
                            segment.sum_wcet += int(tmp.wcets[tmp.c_init][tmp.bw_init])
                            task_done = True
                        else:
                            if verbose_preprocess:
                                print(f"\t\tremaining wcet {tmp.wcets[tmp.c_init][tmp.bw_init]} > seg len {segment.length()}")
                            segment.sum_wcet += int(segment.length())
                            tmp.wcets[tmp.c_init][tmp.bw_init] -= int(segment.length())
                            assert tmp.wcets[tmp.c_init][tmp.bw_init] > 0, "WOAH, UPDATED WCET IS <= 0?!"

                        segment.threshold = segment.sum_wcet / segment.length()
                        segment.is_heavy  = segment.threshold > total_threshold
                        segment.partially_contained_tasks.append(subtask)
                        if task_done:
                            break
                assert task_done == True

        # Step 7. THE BIG STRETCH
        wcets_heavy  = 0
        length_light = 0
        for segment in segments:
            if segment.is_heavy:
                wcets_heavy  += segment.sum_wcet
            else:
                length_light += segment.length()
        total_wcets = total_threshold * total_len
        omega = (wcets_heavy / total_wcets) + (length_light / total_len)
        all_omegas.append(omega)

        assert not dag_task[-1].children, "WOAH, sink node SHOULD NOT have children"
        util = total_wcets / dag_task[-1].period
        all_Utils.append(util)

        # sanity check
        assert segment_times[-1] == dag_task[-1].deadline, "WOAH, LAST SEGMENT BOUNDARY IS NOT WHAT WE EXPECT"
        gamma = dag_task[-1].deadline / dag_task[-1].period
        all_gammas.append(gamma)

        for i in range(len(segments)):
            segment = segments[i]
            if verbose_preprocess:
                print(f"calc new segment end during stretch, length: {segment.length()}, omega: {omega}, gamma: {gamma}")
            if not segment.is_heavy:
                segment.end = segment.length() / (omega * gamma) + segment.start
                assert segment.end > 0
            else:
                segment.end = segment.sum_wcet / (omega * util) + segment.start
                assert segment.end > 0

            # update child
            if i+1 < len(segments):
                orig_length = segments[i+1].length()
                segments[i+1].start = segment.end
                segments[i+1].end = segments[i+1].start + orig_length

        if verbose_preprocess:
            print("STRETCHING DONE, SEGMENTS:")
            for segment in segments:
                print(segment)

        # Step 8. Recalucate release and deadlines
        for subtask in dag_task:
            earliest_start = float("inf")
            latest_end = 0
            for segment in segments:
                start = segment.start
                end   = segment.end
                if task_is_in_copy_list(subtask, segment.fully_contained_tasks) or task_is_in_copy_list(subtask, segment.partially_contained_tasks):
                    if start < earliest_start:
                        earliest_start = start
                    if end > latest_end:
                        latest_end = end
            subtask.release_offset = int(earliest_start)
            subtask.deadline   = int(latest_end)
            subtask.reset_deadline = int(subtask.deadline)
            #real_task.cur_finish = real_task.deadline
            cur_phase, phase_idx = find_phase(subtask, 1, subtask.c_init, subtask.bw_init)
            subtask.cur_finish = int(subtask.release_offset + calc_ttf(subtask, 1, cur_phase, phase_idx, subtask.max_insn, subtask.c_init, subtask.bw_init))

        # Step 9. TAKE THE RES to fill the stretch
        if algo_type == ALGO_RASCO:
            for subtask in dag_task:

                while True:
                    c, bw = select_least_impactful_res_under_wcet_constraint(subtask, subtask.deadline - subtask.release_offset)
                    if c == 0 and bw == 0:
                        break
                    subtask.c_init  -= c
                    subtask.bw_init -= bw

                    #print(f"take away res from {task.uid}, new res c {task.c} bw {task.bw}")
                    if subtask.c_init == 2 or subtask.bw_init == 2:
                        break


            # last step, set up the release times and deadlines correctly one last time using min_c and min_bw
            for subtask in dag_task:
                if not subtask.parents:
                    subtask.release_offset = 0
                else:
                    subtask.release_offset = int(max(parent.cur_finish for parent in subtask.parents))
                #task.deadline   = task.release_offset + task.wcets[task.min_c][task.min_bw]
                #tmp = task.deadline
                #task.deadline   = int(task.release_offset + calc_ttf(task, 1, task.max_insn, task.min_c, task.min_bw))
                cur_phase, phase_idx = find_phase(subtask, 1, subtask.c_init, subtask.bw_init)
                subtask.cur_finish = int(subtask.release_offset + calc_ttf(subtask, 1, cur_phase, phase_idx, subtask.max_insn, subtask.c_init, subtask.bw_init))
                assert subtask.deadline <= subtask.dag_deadline

        # Step 10. Make sure that the release times are set to cur_finish times, to enable early release and not late release
        if algo_type != ALGO_RASCO:
            for subtask in sorted(dag_task, key=lambda subtask: subtask.deadline):
                if len(subtask.parents) == 0:
                    assert subtask.release_offset == 0
                else:
                    subtask.release_offset = int(max(parent.cur_finish for parent in subtask.parents))

                subtask.cur_finish = int(subtask.release_offset + subtask.wcets[subtask.c_init][subtask.bw_init])
                assert subtask.deadline <= subtask.dag_deadline
                assert subtask.deadline > 0


        if verbose_preprocess:
            print("---------TASK GRAPH MIN ALLOC DONE:-------------")
            #print_DAG(dag_task)
            print("------------------------------------------------\n")

    return all_Utils, all_gammas, all_omegas    


#  ============================== RASCO HELPER FUNCTIONS ==============================  #

def get_all_jobs(taskset):
    """Get the set of all jobs (\mathcal{J}) in one hyperperiod from the list of all Subtask objects and the set of all anchor points (\mathcal{A})

    Args:
        all_subtasks: A list of all Subtask objects in the task set.

    Return:
        all_jobs: A list of all Jobs objects in one hyperperiod.
        anchor_points: All anchor points (DAG task release times)
    """

    all_jobs = []
    anchor_points = set()
    
    hyper_period_value = compute_hyper_period(taskset)
    #print(f"hyper period: {hyper_period_value}")

    # Iterate over all DAG tasks in the task set
    for dag_task in taskset:
        task_period = dag_task[0].period
        num_releases = int(hyper_period_value / task_period)

        # For each task release
        for release_num in range(num_releases):
            # Compute the anchor point
            anchor_point = task_period*release_num
            anchor_points.add(anchor_point)

            # Create the job instances from the subtasks of this DAG task
            jobs_of_this_task_release = []
            for subtask in dag_task:
                new_job = Job(subtask, release_num, anchor_point)
                jobs_of_this_task_release.append(new_job)

            # Update the parent and children pointers
            for subtask in dag_task:
                for job in jobs_of_this_task_release:
                    # For each job that is equivalent to some subtask
                    if subtask.uid == job.uid:
                        # Given the parents of the subtask
                        for subtask_parent in subtask.parents:
                            # Find the jobs that should be parents of the job
                            for job_parent in jobs_of_this_task_release:
                                if subtask_parent.uid == job_parent.uid:
                                    job.parents.append(job_parent)
                        # Given the children of the subtask
                        for subtask_child in subtask.children:
                            # Find the jobs that should be children of the job
                            for job_child in jobs_of_this_task_release:
                                if subtask_child.uid == job_child.uid:
                                    job.children.append(job_child)
                    assert job.deadline > 0

            # Now update the uids of the job objects to reflect the release number
            for job in jobs_of_this_task_release:
                job.uid = f"{job.uid}_{job.release_num}"

            # Add these jobs to the set of all jobs
            all_jobs.extend(jobs_of_this_task_release)

    # Sort the set of all jobs by release_offsets
    all_jobs.sort(key=lambda job: job.release_offset)
    return all_jobs, anchor_points


def check_if_overallocated(sched_set, res_sched, t, tnext):
    """Checks if sched set is overallocatin resources and removes resources from the jobs with most slack.
    
    Args:
        sched_set: set of jobs with earliest deadlines
        res_sched: resources used by sched set
        t: current decision point
        tnext: next decision point
        
    Returns:
        sched_set: set of jobs with earliest deadlines
        res_sched: resources used by sched set without overallocation
    """

    # Find job in sched_set with smallest completion time, check if it defines tnext
    job_defining_tnext = min(sched_set, key=lambda job: job.cur_finish)
    if job_defining_tnext is not None:
        assert job_defining_tnext.cur_finish >= tnext, f"Job {job_defining_tnext} finishes earlier than tnext={tnext}"
        if job_defining_tnext.cur_finish > tnext:
            job_defining_tnext = None

    while res_sched.get('c') > MAX_CACHE_ITR or res_sched.get('bw') > MAX_MEMBW_ITR:
        jobs_sorted_by_slack = sorted(sched_set, reverse=True, key=lambda job: job.dag_deadline - job.cur_finish)
        chosen_job = None
        for job in jobs_sorted_by_slack:
            if job_defining_tnext is not None and job.uid == job_defining_tnext.uid:
                # If this is the job that defines tnext, we don't want to remove resources from it (for termination reasons)
                continue
            # If both resource types are over max., take least impactful one from job with most slack
            if res_sched.get('c') > MAX_CACHE_ITR and res_sched.get('bw') > MAX_MEMBW_ITR:
                c, bw = select_least_impactful_res(job)
                if c == 0 and bw == 0: # If both job.c and job.bw are at the min, (c, bw) = (0, 0) will be returned, try next job in jobs_sorted_by_slack
                    continue
                else: # One of c or bw will be 1, the other 0
                    job.c -= c
                    job.bw -= bw
                    chosen_job = job
                    break
            # If one resource type is over max and we can take it from this job, do so
            elif job.c > 2 and res_sched.get('c') > MAX_CACHE_ITR:
                job.c -= 1
                chosen_job = job
                break
            # If other resource type is over max and we can take it from this job, do so
            elif job.bw > 2 and res_sched.get('bw') > MAX_MEMBW_ITR:
                job.bw -= 1
                chosen_job = job
                break

        assert chosen_job is not None, print(f"length of sched set is {len(sched_set)}")
        # Update the total budget used
        res_sched = {'c': sum(job.c for job in sched_set), 'bw': sum(job.bw for job in sched_set)}

        # Update cur_finish, may need to update tnext as well
        chosen_job.cur_finish = int(calc_task_finish(chosen_job, t, tnext))

    return sched_set, res_sched


def release_successors(job, algo_type):
    """Given a job that just completed, check if any of its children should be released now.
    
    Args:
        job: The job that just completed.
        
    Returns:
        A list of jobs that were just released (or empty list if none).
    """

    released_jobs = []
    for child in job.children:
        if all(parent.complete for parent in child.parents):
            released_jobs.append(child)
            child.release_offset = job.cur_finish

    for released_job in released_jobs:
        if algo_type != ALGO_RASCO:
            released_job.cur_finish = released_job.release_offset + int((released_job.max_insn - released_job.cur_insn) / released_job.even_rate)  
        else:
            assert released_job.c == released_job.c_init and released_job.bw == released_job.bw_init, "c and bw must be equal to c_init and bw_init before release"
            released_job.cur_finish = int(calc_task_finish(released_job, released_job.release_offset, sys.maxsize))

    return released_jobs


def is_in_set(set, job):
    """Given a job and a set of jobs, check if job in set.
    
    Args:
        set: The set of jobs.
        job: The job to check for.
        
    Returns:
        True if job in set, false otherwise.
    """

    for other_job in set:
        if other_job.uid == job.uid:
            return True
        
    return False


def find_phase(task, target_insn, target_cache, target_membw):
    """Optimized version with binary search and caching"""
    all_res_phase_entries = task.get_phase_ref()
    
    if all_res_phase_entries is None or all_res_phase_entries[target_cache-1][target_membw-1] is None:
        return None, -1
    
    phases = all_res_phase_entries[target_cache-1][target_membw-1]

    if target_insn > phases[-1].insn_end:
        return None, -1
    
    # Binary search instead of linear search
    left, right = 0, len(phases) - 1
    
    while left <= right:
        mid = (left + right) // 2
        phase = phases[mid]
        
        if phase.insn_start <= target_insn <= phase.insn_end:
            return phase, mid
        elif target_insn < phase.insn_start:
            right = mid - 1
        else:
            left = mid + 1
    
    return None, -1



# We want to return the time needed to go from cur_insn to max_insn given alloc
# of [c,bw] across all phases
verbose_ttf = False
def calc_ttf(task, cur_insn, cur_phase, phase_idx, max_insn, c, bw):
    ttf = 0

    assert c  > 0
    assert bw > 0

    if max_insn < cur_insn:
        print(f"WOAH, ERROR, max_insn < cur_insn")
        print(f"cur_insn: {cur_insn}, max_insn: {max_insn}")
        assert False

    if cur_insn >= max_insn:
        return 0

    #cur_phase, phase_idx = find_phase(task, cur_insn, c, bw)
    if cur_phase == None:
        print(f"Job: {task}")
        print(f"\tCur insn: {cur_insn}, max insn: {max_insn}")
    assert cur_phase != None, "WOAH ERROR, cur_phase in calc_ttf is NONE!"
    insn_to_complete = cur_phase.insn_end - cur_insn
    while cur_insn < max_insn:
        assert cur_phase.insn_rate > 0, "WOAH, ERROR, cur_phase rate is <= 0?!"
        #ttf += insn_to_complete / (cur_phase.insn_rate / 1000000) # convert ms to ns
        ttf += int(insn_to_complete / (cur_phase.insn_rate / 1000000000) + 1) # convert s to ns

        if verbose_ttf:
            print(f"\t\tcalc_ttf, task {task.uid}, insn_to_complete {insn_to_complete}, max {max_insn}, cur {cur_insn}, at rate {cur_phase.insn_rate / 1000000000}, cur_ttf: {ttf}")

        # get the next phase
        cur_insn = cur_phase.insn_end+1
        #print(f"phase_idx {phase_idx}, next cur_insn {cur_insn}, max_insn {max_insn}")
        if cur_insn >= max_insn:
            # there is no next phase
            break
        # OPTIMIZATION, WE KNOW ITS GOING TO BE IMMEDIATE NEXT PHASE, JUST ACCESS IT DIRETLY, DON'T SEARCH
        #cur_phase = find_phase(task, cur_insn, c, bw)
        #print(f"cur_insn {cur_insn}, max_insn {max_insn}")
        cur_phase = task.get_phase_ref()[c-1][bw-1][phase_idx+1]
        phase_idx += 1
        assert cur_phase != None, "WOAH ERROR, cur_phase in calc_ttf is NONE!"
        assert cur_phase.insn_start <= cur_insn
        assert cur_phase.insn_end   >= cur_insn, print(f"cur_phase.insn_start: {cur_phase.insn_start}, cur_phase.insn_end: {cur_phase.insn_end}, cur_insn: {cur_insn}, max_insn: {max_insn}")

        # Time needed to finish current phase, given current phase's rate
        insn_to_complete = cur_phase.insn_end - cur_phase.insn_start
        assert insn_to_complete >= 0, "WOAH, ERROR, insn_to_complete is < 0"

    if ttf <= 0:
        print(f"WOAH, TTF <= 0?!: {ttf}")
        print(task)
        assert False
    return ttf

# return the number of instructions finished over time starting from cur_insns
def calc_insn_in_range(task, cur_insn, cur_phase, phase_idx, rem_time, c, bw):
    insn_tot = 0
    #cur_phase = None
    cur_phase_idx = -1

    if cur_insn > task.max_insn:
        return 0

    while True:
        if cur_phase_idx == -1:
            cur_phase_idx = phase_idx
        else:
            # OPTIMIZATION, WE KNOW ITS GOING TO BE IMMEDIATE NEXT PHASE, JUST ACCESS IT DIRETLY, DON'T SEARCH
            try:
                cur_phase = task.get_phase_ref()[c-1][bw-1][cur_phase_idx+1]
                assert cur_phase.insn_rate > 0
                cur_phase_idx += 1
            except Exception as e:
                print(e)
                #print_DAG(dag)
                #draw_DAG(dag, "tmp")
                return -1

        assert cur_phase != None, "WOAH ERROR, cur_phase in calc_ttf is NONE!"

        #print(f"cur_phase start: {cur_phase.insn_start}, end {cur_phase.insn_end}, rem time: {rem_time}, insn tot: {insn_tot}")

        cur_phase_time = calc_ttf(task, cur_insn, cur_phase, cur_phase_idx, cur_phase.insn_end, c, bw)
        assert cur_phase_time > 0

        if cur_phase_time == rem_time:
            insn_tot += cur_phase.insn_end - cur_insn
            return (int)(insn_tot)
        if cur_phase_time < rem_time:
            rem_time -= cur_phase_time
            insn_tot += cur_phase.insn_end - cur_insn
        else:
            break

        cur_insn = cur_phase.insn_end+1

        if cur_insn >= task.max_insn:
            return  (int)(insn_tot)

    # Handle last phase case, cur_phase_time > rem_time
    # time left available is rem_time
    #insn_tot += (cur_phase.insn_rate / 1000000) * rem_time
    insn_tot += (cur_phase.insn_rate / 1000000000) * rem_time

    return min((int)(insn_tot), task.max_insn - task.cur_insn)

# used for calculating the cur_finish for tasks in the current segment
def calc_task_finish(picked_task, t, tnext):
    seg_start = t
    seg_end   = tnext
    cur_insn = picked_task.cur_insn
    max_insn = picked_task.max_insn
    c  = picked_task.c
    bw = picked_task.bw

    if verbose_ttf:
        print(f"\tDEADLINE UPDATE task {picked_task.uid} over seg len {seg_end-seg_start}")

    # are we already done?
    if cur_insn >= max_insn:
        return seg_end

    cur_phase, phase_idx = find_phase(picked_task, cur_insn, c, bw)
    abs_ttf = seg_start + calc_ttf(picked_task, cur_insn, cur_phase, phase_idx, max_insn, c, bw)


    if abs_ttf > seg_end:
        insn_ret_seg = calc_insn_in_range(picked_task, cur_insn, cur_phase, phase_idx, seg_end-seg_start, c, bw)
        assert insn_ret_seg >= 0, f"insn_ret_in_seg: {insn_ret_seg}, cur insn: {cur_insn}, seg length: {seg_end-seg_start}, job: {picked_task}"
        if cur_insn + insn_ret_seg > max_insn:
            return seg_end
        cur_phase, phase_idx = find_phase(picked_task, cur_insn + insn_ret_seg, picked_task.c_init, picked_task.bw_init)
        abs_ttf = seg_end + calc_ttf(picked_task, cur_insn + insn_ret_seg, cur_phase, phase_idx, max_insn, picked_task.c_init, picked_task.bw_init)

    if verbose_ttf:
        print(f"\tDEADLINE UPDATE task {picked_task.uid} c {picked_task.c} bw {picked_task.bw}, abs_ttf: {abs_ttf}, seg_end: {seg_end}")

    return abs_ttf


verbose_res_alloc = False
def allocate_resource(ready_set, sched_set, res_used_by_sched, segment_len):
    """
    Given a taskset, return the task that benefits the most from one additional resource partition
        Note: Remaining c and bw to give out is restricted for sched_set, but not for all other tasks in ready_set

    Args:
        ready_set: All jobs that are currently release in segment.
        sched_set: The set of jobs with the earliest deadlines.
        res_used_by_sched: The total resource budget used by sched_set.
        segment_len: The length of the current segment.

    Return:
        The chosen job as well as which resource in the form of c, bw where c or bw will equal 1, but not both.

    """
    picked_task = None
    picked_c = 0
    picked_bw = 0

    if verbose_res_alloc:
        print("Running Iterative Resource Allocation")

    best_theta = -1
    used_c  = res_used_by_sched.get('c')
    used_bw = res_used_by_sched.get('bw')
    rem_c  = MAX_CACHE_ITR - used_c
    rem_bw = MAX_MEMBW_ITR - used_bw 

    if rem_c == 0 and rem_bw == 0:
        return picked_task, picked_c, picked_bw

    if verbose_res_alloc:
        print(f"rem_c: {rem_c}, rem_bw: {rem_bw}")
        #if rem_c < 0 or rem_bw < 0:
            #print_DAG(sched_set)
    assert rem_c  >= 0, "rem_c is netagive?!"
    assert rem_bw >= 0, "rem_bw is netagive?!"

    for task in ready_set:
        if task.c == MAX_CACHE_ITR and task.bw == MAX_MEMBW_ITR:
            continue

        if task.c == MAX_CACHE_ITR and rem_bw == 0:
            continue

        if task.bw == MAX_MEMBW_ITR and rem_c == 0:
            continue

        if verbose_res_alloc:
            print(f"considering task: {task}")
        # Find the current phase this task is in
        phase, phase_idx = find_phase(task, task.cur_insn, task.c, task.bw)
        if phase == None or task.cur_insn > task.max_insn:
            assert False, f"task should not be in ready set, it is done already"

        insn = task.cur_insn
        assert segment_len > 0
        insn_in_range = min(calc_insn_in_range(task, insn, phase, phase_idx, segment_len, task.c, task.bw), task.max_insn - insn)
        abs_insns_over_segment = insn + insn_in_range
        if abs_insns_over_segment == insn:
            continue
        if abs_insns_over_segment <= 0:
            print(f"woah, insn_over_segment <= 0: {abs_insns_over_segment}, task {task.uid}, insn: {insn}: segment len: {segment_len}, c {task.c} bw {task.bw}")
            assert False

        # Start checking thetas for abs_insns_over_segment length
        total_theta_val = 0
        cache_which_insn_sum = 0
        membw_which_insn_sum = 0
        # iterate over all phases in segment
        while phase != None and insn < task.max_insn:

            if phase.insn_start >= abs_insns_over_segment:
                break

            if task in sched_set:
                if verbose_res_alloc:
                    print("\tThis task is in sched set")
                rem_c =  min(MAX_CACHE_ITR - task.c, rem_c)
                rem_bw = min(MAX_MEMBW_ITR - task.bw, rem_bw)
                theta_val   = phase.theta_set[rem_c][rem_bw].value
                theta_which = phase.theta_set[rem_c][rem_bw].which
                if theta_val == 0:
                    print(f"WOAH 1, why is theta 0 when rem_c is {rem_c} and rem_bw is {rem_bw} and cur_c is {task.c} and cur_bw is {task.bw} ?!")
                    for c in range(rem_c+1):
                        for bw in range(rem_bw+1):
                            print(f"theta rem_c: {c} rem_bw: {bw}, {phase.theta_set[c][bw]}")
                    assert False
                if verbose_res_alloc:
                    print(f"\tSubtask's theta given rem_c and rem_bw: {theta_val}, which: {theta_which}")
            else:
                if verbose_res_alloc:
                    print("\tThis task is not in sched set")
                theta_val   = phase.theta_set[MAX_CACHE_ITR - task.c][MAX_MEMBW_ITR - task.bw].value
                theta_which = phase.theta_set[MAX_CACHE_ITR - task.c][MAX_MEMBW_ITR - task.bw].which
                if theta_val == 0:
                    print(f"WOAH 2, why is theta 0 when rem_c is {rem_c} and rem_bw is {rem_bw} and cur_c is {task.c} and cur_bw is {task.bw} ?!")
                    for c in range(rem_c+1):
                        for bw in range(rem_bw+1):
                            print(f"theta rem_c: {c} rem_bw: {bw}, {phase.theta_set[c][bw]}")
                    assert False
                if verbose_res_alloc:
                    print(f"\tSubtask's theta given rem_c and rem_bw: {theta_val}, which: {theta_which}")

            # sanity checks
            assert phase.insn_end >= insn
            assert insn >= phase.insn_start

            # use the current theta which value to increase the corresponding which_insn_sum
            insn_per_phase = 0
            if phase.insn_end > abs_insns_over_segment:
                insn_per_phase = abs_insns_over_segment - phase.insn_start
            else:
                insn_per_phase = phase.insn_end - insn
            if theta_which == 1:
                membw_which_insn_sum +=insn_per_phase 
            else:
                cache_which_insn_sum += insn_per_phase

            # use the current theta value to increase total_theta_val
            assert insn_per_phase > 0, print(f"insn_start: {phase.insn_start}, insn_end: {phase.insn_end}, abs_insns_over_segment: {abs_insns_over_segment}, insn: {insn}")
            total_theta_val += theta_val * insn_per_phase 

            if phase.insn_end >= abs_insns_over_segment:
                break

            phase = task.get_phase_ref()[task.c-1][task.bw-1][phase_idx+1]
            if phase == None:
                break
            phase_idx += 1
            insn = phase.insn_start
            #if phase.insn_end >= abs_insns_over_segment:
            #    break

        # USE TOTAL THETA VAL FOR THIS TASK
        if total_theta_val == 4:
            total_theta_val = 1
        else:
            total_theta_val = total_theta_val / (abs_insns_over_segment - task.cur_insn)
        assert total_theta_val >= 0

        if verbose_res_alloc:
            print(f"total_theta_val {total_theta_val}, best_theta {best_theta}")
            print(f"cache_which_insn_sum {cache_which_insn_sum}, membw_which_insn_sum {membw_which_insn_sum}")

        if total_theta_val > best_theta:
            best_theta = total_theta_val
            picked_task = task
            if membw_which_insn_sum > cache_which_insn_sum:
                picked_c  = 0
                picked_bw = 1
            else:
                picked_c  = 1
                picked_bw = 0

    if best_theta == 1:
        # this means that all tasks would stay in the same phase if given any resource
        # tie break: allocate to task with smallest current c + bw total
        smallest_task = None
        smallest_sum  = MAX_CACHE_ITR + MAX_MEMBW_ITR
        for task in ready_set:
            if task.c == MAX_CACHE_ITR and task.bw == MAX_MEMBW_ITR:
                continue
            sum = task.c + task.bw
            if sum < smallest_sum:
                smallest_task = task
                smallest_sum  = sum

        if smallest_task == None:
            return None, 0, 0

        if smallest_task not in sched_set:
           rem_c = MAX_CACHE_ITR - smallest_task.c
           rem_bw = MAX_MEMBW_ITR - smallest_task.bw

        assert smallest_task.c + smallest_task.bw < MAX_CACHE_ITR + MAX_MEMBW_ITR
        # Give a resource to smallest task
        if (smallest_task.c <= smallest_task.bw) and rem_c > 0:
            return smallest_task, 1, 0
        elif (smallest_task.bw <= smallest_task.c) and rem_bw > 0:
            return smallest_task, 0, 1
        elif rem_c > 0:
            return smallest_task, 1, 0
        else: 
            return smallest_task, 0, 1

    return picked_task, picked_c, picked_bw


def get_tnext(job_set, anchor_points, t):
    """Get the next release or completion time of any job in job_set after time t

    Args:
        ready_set: the set of jobs that are ready to be scheduled.
        anchor_points: the list of anchor points (DAG job releases).
        t: The current decision point.

    Return:
        tnext: The next decision point after t given jobs.
    """

    future_anchor_points = [anchor_point for anchor_point in anchor_points if anchor_point > t]
    if future_anchor_points and job_set:
        tnext = min(min(future_anchor_points), min(job.cur_finish for job in job_set))
    elif future_anchor_points:
        tnext =  min(future_anchor_points)
    elif job_set:
        tnext = min(job.cur_finish for job in job_set)

    return tnext


def select_least_impactful_res(task):
    """Returns the resource that causes the smallest increase in wcet
    
    Args:
        task: The subtask object.
    
    Returns:
        (c, bw): one of the values will be 1 the other 0
    """

    if task.c <= 2 and task.bw <= 2:
        return 0, 0
    
    # If one res is at minimum, take away other
    if task.c <= 2:
        return 0, 1
    elif task.bw <= 2:
        return 1, 0
    
    # General case
    cache_wcet = task.wcets[task.c-1][task.bw]
    membw_wcet = task.wcets[task.c][task.bw-1]
    
    # Take the smallest impact
    if cache_wcet <= membw_wcet:
        return 1, 0
    else:
        return 0, 1


def reorder_jobs(prev_sched_job_uids, sched_set):
    '''Returns the set of jobs.

    Args:  
        prev_sched_job_uids: Set of job uids in previous segment (None if core is idle).
        sched_set: Set of job objects chosen for current segment.

    Return: 
        Set of job objects in current segment ordered by prefered core.
    '''

    # Initialize new list for ordered jobs
    reordered_sched_set = [None] * NUM_CPUS
    # Keep track of jobs that can go on any core (not in prev segment and no parents in prev segment)
    unordered = []

    for job in sched_set:
        ordered = False
        # Check if self was in prev segment
        for prev_idx, prev_uid in enumerate(prev_sched_job_uids):
            if prev_uid == job.uid:
                reordered_sched_set[prev_idx] = job
                ordered = True
                break
        # If not, check if parent job was in prev segment
        if not ordered:
            for prev_idx, prev_uid in enumerate(prev_sched_job_uids):
                for parent in job.parents:
                    if prev_uid == parent.uid and not reordered_sched_set[prev_idx]:
                        reordered_sched_set[prev_idx] = job
                        ordered = True
                        break
                if ordered:
                    break
        # If neither, place anywhere
        if not ordered:
            unordered.append(job)

    # Place all the unordered jobs
    for job in unordered:
        for reordered_idx, reordered_task in enumerate(reordered_sched_set):
            if reordered_task is None:
                reordered_sched_set[reordered_idx] = job
                break  # Exit the inner loop once placed

    return reordered_sched_set