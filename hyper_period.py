def gcd(a, b):
    """Helper function to compute the greatest common divisor using Euclid's algorithm."""

    while b:
        a, b = b, a % b
    return a

def lcm(a, b):
    """Helper function to compute the least common multiple of two numbers."""

    return abs(a * b) // gcd(a, b)

def compute_hyper_period(taskset):
    """Compute the hyper-period of a set of real-time tasks based on the absolute deadlines of the last tasks in each independent chain.
    Args: 
        taskset: A list of DAG tasks in the task set, each DAG task is a list of Subtask objects.
    Return: 
        The hyper-period (LCM of the periods of all DAG tasks).
    """

    # Get a subtask from each DAG task (every subtask in a DAG has the same period)
    periods = []
    for dag_task in taskset:
        periods.append(dag_task[0].period)
    
    if not periods:
        return 0
    
    hyper_period = periods[0]
    for period in periods[1:]:
        hyper_period = lcm(hyper_period, period)

    return hyper_period