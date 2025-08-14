import os
import sys
import re
import algo

verbose_parser = False

def fetch_wcets(workload_name):
    '''Get the WCETs and max instruction count for a profiled workload.

    Args:  
        workload_name: The name of the workload to get.

    Return: 
        wcets: A double array of WCETs for each resource budget configuration.
        max_insn: The maximum instruction count for the workload.
    '''

    # Initialize the double array wcets to store values for cache_itr from 1 to 20 and bandwidth_itr from 1 to MAX_CACHE_ITR
    wcets = [[0.0 for _ in range(algo.MAX_CACHE_ITR+1)] for _ in range(algo.MAX_MEMBW_ITR+1)]
    max_insn = 0
    
    # Loop over cache_itr from 2 to 20
    for cache_itr in range(2, algo.MAX_CACHE_ITR+1):
        # Calculate cache_allocation as a value with cache_itr bits set to 1
        cache_allocation = (1 << cache_itr) - 1

        # Loop over bandwidth_itr from 2 to 20
        for bandwidth_itr in range(2, algo.MAX_MEMBW_ITR+1):
            # Calculate bandwidth_allocation
            bandwidth_allocation = bandwidth_itr * 72

            # Construct the directory path for the current cache and bandwidth allocation
            directory_path = f"./profiles/{workload_name}/{cache_allocation}_{bandwidth_allocation}"
            #print(f"Fetching wcet at path {directory_path}")
            wcet_file_path = os.path.join(directory_path, "wcet.txt")

            # Read the wcet.txt file if it exists
            if os.path.exists(wcet_file_path):
                with open(wcet_file_path, "r") as wcet_file:
                    first_line = wcet_file.readline().strip()
                    #print(f"saving wcet value {float(first_line)*1e9} to wcets[{cache_itr}][{bandwidth_itr}]")
                    # Convert to ns
                    wcets[cache_itr][bandwidth_itr] = int(float(first_line) * 1e9)
                    second_line = wcet_file.readline().strip()
                    tmp = float(second_line)
                    if tmp > max_insn:
                        max_insn = tmp
            else:
                print(f"Warning: Missing wcet.txt file in {directory_path}")

    # Return the double array wcets
    return wcets, int(max_insn)


def process_gml_file(file_path):
    '''Processes the .gml file which contains information about the structure of a single task graph.

    Args:  
        file_path: The path to the .gml file.

    Return: 
        dag_task: A list of subtask objects that make up the task graph.
        U: The task graph utilization.
    '''

    global uid_offset
    parents_ids = {}
    children_ids = {}
    uids = {}
    workload_names = {}
    dag_task = [] # collection of Subtask objects
    U = None
    T = None
    W = None
    Index = None

    # Updated Regex patterns for Index, U, T, W, node, and edge
    header_pattern = re.compile(r"Index (\d+)\s*U ([\d.]+)\s*T \"([\d.]+)\"\s*W ([\d.]+)")
    node_pattern = re.compile(r"node \[\s*id (\d+)\s*label \"\d+\"(?:\s*rank \d+)?\s*C [\d.]+\s*type \"(\w+)\"\s*\]")
    edge_pattern = re.compile(r"edge \[\s*source (\d+)\s*target (\d+)\s*label \"\d+\"\s*\]")

    with open(file_path, 'r') as file:
        content = file.read()

        # Extract Index, U, T, W
        header_match = header_pattern.search(content)
        if header_match:
            Index = int(header_match.group(1))
            U = float(header_match.group(2))
            T = float(header_match.group(3))
            W = float(header_match.group(4))

        # Extract nodes
        nodes = node_pattern.findall(content)
        for node_id, node_type in nodes:
            id = int(node_id) + uid_offset
            uids[id] = id
            workload_names[id] = node_type
            parents_ids[id] = set()  # Initialize parents set for each node
            children_ids[id] = set()  # Initialize children set for each node

        # Extract edges
        edges = edge_pattern.findall(content)
        for source, target in edges:
            source = int(source) + uid_offset
            target = int(target) + uid_offset
            parents_ids[target].add(source)
            children_ids[source].add(target)

    if verbose_parser:
        print(f" -------------- TASKSET IDX: {Index}, U: {U}, period: {T}, dag_deadline: {W} --------------")

    # Create Subtask objects
    for id in range(uids[uid_offset], uids[uid_offset]+len(uids)):
        if verbose_parser:
            print(f"index {id} has node {uids[id]}, type {workload_names[id]}, parents {parents_ids[id]}, children  {children_ids[id]}")

        wcets, max_insn = fetch_wcets(workload_names[id])
        assert max_insn != float('inf'), "ERROR, FAILED TO GET MAX_INSN VALUE"

        subtask_dict = {'name': workload_names[id], 'p': int(T), 'wcets': wcets}
        subtask_dict['uid'] = uids[id]
        subtask_dict['max_insn'] = int(max_insn)
        new_subtask = algo.Subtask(subtask_dict) # set parents and children afterwards, once all subtask objects are created

        dag_task.append(new_subtask)

    # Set parents and children for each subtask in the dag_task
    for child in dag_task:
        for parent in dag_task:
            if parent.uid in parents_ids[child.uid]:
                child.parents.append(parent)
                parent.children.append(child)
    
    # Increment offset so that task graph 2's source node uid starts at task graph 1's sink node uid+1
    uid_offset += len(uids)

    return dag_task, U


def parse_taskset(taskset_path, taskset_util, taskset_idx):
    '''Processes the DAG task .gml files for the taskset in folder ./{taskset_path}/data-multi-m{NUM_CPUS}-u{taskset_util}/{taskset_idx}

    Args:  
        taskset_path: The path to the data-multi-m{NUM_CPUS}-u{taskset_util} folders.
        taskset_util: The total utilization of the task set.
        taskset_idx: The index of the task set for the target utilization.

    Return: 
        taskset: A list of all DAG tasks in the task set, each DAG task is a list of Subtask objects
    '''

    print("Taskset path: " + taskset_path)
    print("Taskset target util: " + f"{taskset_util}")
    print("\t taskset idx: " + str(taskset_idx))

    # Keep track of the uid_offset so that task graph 2's source node uid starts at task graph 1's sink node uid+1
    global uid_offset
    uid_offset = 0
    U_sum = 0

    taskset = []
    full_path = os.path.join(taskset_path, "data-multi-m" + str(algo.NUM_CPUS) +"-u" + f"{taskset_util}", f"{taskset_idx}") 

    if verbose_parser:
        print(full_path)

    for file_name in os.listdir(full_path):
        if file_name.startswith("Tau_") and file_name.endswith(".gml"):
            file_path = os.path.join(full_path, file_name)
            dag_task, U = process_gml_file(file_path)
            U_sum += U
            taskset.append(dag_task)

    return taskset, U_sum

def print_taskset(taskset):
    for dag_task in taskset:
        for subtask in dag_task:
            print(subtask)