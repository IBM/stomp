
from meta import BaseMetaPolicy
from meta import max_length

class TaskVariables:
    def __init__(self):
        pass

class DAGVariables:
    def __init__(self):
        pass

class MetaPolicy(BaseMetaPolicy):

    def init(self, params):
        pass

    def set_task_variables(self, dag, task_node):
        return None

    def set_dag_variables(self, dag):
        return None

    def meta_static_rank(self, stomp, dag):
        pass

    def meta_dynamic_rank(self, stomp, task, comp, max_time, min_time, deadline, priority): 

        wcet_slack = deadline - max_time
        bcet_slack = deadline - min_time
        if (priority > 1):
            if (wcet_slack >= 0):
                slack = 1 + wcet_slack
                task.rank = int((100000 * (priority))/slack)
                task.rank_type = 3 
            elif (bcet_slack >= 0):
                slack = 1 + bcet_slack
                task.rank = int((100000 * (priority))/slack)
                task.rank_type = 4 
            else:
                slack = 1 + 0.99/bcet_slack
                task.rank = int((100000 * (priority))/slack)
                task.rank_type = 5 
        else:
            if (wcet_slack >= 0):
                slack = 1 + wcet_slack
                task.rank = int((100000 * (priority))/slack)
                task.rank_type = 2 
            elif (bcet_slack >= 0):
                slack = 1 + bcet_slack
                task.rank = int((100000 * (priority))/slack)
                task.rank_type = 1 
            else:
                slack = 1 + 0.99/bcet_slack
                task.rank = int((100000 * (priority))/slack)
                task.rank_type = 0

    def dropping_policy(self, dag, task_node): 
        ex_time = max_length(dag.graph, task_node) #BCET of critical path
        if(dag.slack - ex_time < 0 and dag.priority == 1):
            dag.dropped = 1
            return True
        
        return False
           
