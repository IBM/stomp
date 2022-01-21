class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class events:
    META_START = 0
    TASK_ARRIVAL = 1
    DAG_ARRIVAL = 2
    SERVER_FINISHED = 3
    TASK_COMPLETED = 4
    META_DONE = 5
    SIM_LIMIT = 6
