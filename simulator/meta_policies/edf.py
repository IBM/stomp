
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
        pass
        
    def dropping_policy(self, dag, task_node):        
        return False
           
