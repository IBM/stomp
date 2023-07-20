
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

    def meta_dynamic_rank(self, stomp, task, comp, deadline, priority): 

        wcet_slack = deadline - task.max_time
        bcet_slack = deadline - task.min_time
        if (wcet_slack >= 0):
            # WCET deadline exists
            slack = 1 + wcet_slack
            task.rank = int((100000 * (priority))/slack)
        else:
            # Missed WCET deadline
            slack = 1 + 0.99/wcet_slack
            task.rank = int((100000 * (priority))/slack)

    def dropping_policy(self, dag, task_node): 
        ex_time = max_length(dag.graph, task_node) #BCET of critical path
        if(dag.slack - ex_time < 0 and dag.priority == 1):
            dag.dropped = 1
            return True
        
        return False
           
