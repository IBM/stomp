
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


        if ((deadline - (max_time)) < 0):
            if (priority > 1):
                if((deadline - (min_time)) >= 0):
                    slack = 1 + (deadline - (min_time))
                    task.rank = int((100000 * (1000000*priority))/slack)
                    task.rank_type = 4 
                else:
                    slack = 1 - 0.99/( min_time - deadline)
                    task.rank = int((100000 * (10000000*priority))/slack)
                    task.rank_type = 5 

            else:
                if((deadline - (min_time)) >= 0):
                    slack = 1 + (deadline - (min_time))
                    task.rank = int((100000 * (100*priority))/slack) 
                    task.rank_type = 1                       
                else:
                    slack = 1 - 0.99/( min_time - deadline)
                    task.rank = int((100000 * (1*priority))/slack)
                    task.rank_type = 0
        else:
            slack = 1 + (deadline - (max_time))
            task.rank = int((100000 * (priority))/slack)
            if (task.priority > 1):
                task.rank = int((100000 * (10000*priority))/slack)
                task.rank_type = 3 
            else:
                task.rank = int((100000 * (1000*priority))/slack)
                task.rank_type = 2  
        # print("[%d.%d] Pre Task rank: %d,%d,%d,%d" % (task.dag_id, task.tid, task.rank, priority, deadline, max_time))

    def dropping_policy(self, dag, task_node): 
        ex_time = max_length(dag.graph, task_node) #BCET of critical path
        if(dag.slack - ex_time < 0 and dag.priority == 1):

            dag.dropped = 1
            return True
        
        return False
           