"""
This script is a demonstration of a parallel processing implementation
that leverages the code from approach1.py
"""

import multiprocessing as mp

import approach1 as a1


def illustrate(gender, risk_class, issue_age, face_amount, premium):
    """
    Wrapper function to easily distribute amongst helpers
    """
    rates = a1.get_rates(gender, risk_class, issue_age)
    return a1.illustrate(rates, issue_age, face_amount, premium)


def solve(gender, risk_class, issue_age, face_amount, premium):
    """
    Wrapper function to easily distribute amongst helpers
    """
    return a1.solve_for_premium(gender, risk_class, issue_age, face_amount)


def worker(input: mp.Queue, output: mp.Queue):
    """
    Driver code for individual workers / processes
    """
    for func, args in iter(input.get, 'STOP'):
        result = func(*args)
        output.put(result)


def multi_illustrate(num_tasks: int, num_processes: int):
    """
    Convenience wrapper to perform multiprocessing of illustrate routine
    """
    _multi(num_tasks, num_processes, illustrate)


def multi_solve(num_tasks: int, num_processes: int):
    """
    Convenience wrapper to perform multiprocessing of solve routine
    """
    _multi(num_tasks, num_processes, solve)


def _multi(num_tasks: int, num_processes: int, function):
    """
    Main multiprocessing execution

    Parameters
    ----------
    num_tasks: int
        Number of tasks to generate and execute
    num_processes: int
        Number of parallel processes to run
    function: function
        Actuarial process to run in parallel, "illustrate" or "solve" are valid
    """
    mp.freeze_support()
    tasks = [(function, ('M', 'NS', 35, 100000, 1255.03))
             for _ in range(num_tasks)]

    # create queues
    task_queue = mp.Queue()
    done_queue = mp.Queue()

    # submit tasks
    for task in tasks:
        task_queue.put(task)

    # start workers
    processes = [mp.Process(target=worker, args=(
        task_queue, done_queue)) for _ in range(num_processes)]
    for process in processes:
        process.start()

    # send stop signals
    for _ in range(num_processes):
        task_queue.put('STOP')

    # get results
    for i in range(len(tasks)):
        done_queue.get()

    # rejoin processes
    for process in processes:
        process.join()


if __name__ == '__main__':
    """Example execution"""
    t = 1000
    p = 4
    multi_illustrate(t, p)
