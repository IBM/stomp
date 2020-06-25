
from meta import BaseMetaPolicy
from meta import max_length

class PolicyVariables:
    def __init__(self, R_its_k_heft, ftsched):
        self.ftsched = ftsched
        self.R_its_k_heft = R_its_k_heft

class MetaPolicy(BaseMetaPolicy):

    def init(self, policy):
        pass

    def set_policy_variables(self, dag):
        return PolicyVariables(None, None)

    def meta_static_rank(self, stomp, dag):
        pass

    def meta_dynamic_rank(self, stomp, task, comp, max_time, min_time, deadline, priority): 
        pass
        
    def dropping_policy(self, dag, task_node):        
        return False
           