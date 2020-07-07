
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


        if ((deadline - (max_time)) < 0):
            if (priority > 1):
                if((deadline - (min_time)) >= 0):
                    slack = 1 + (deadline - (min_time))
                    task.rank = int((100000 * (100*priority))/slack)
                else:
                    slack = 1 - 0.99/( min_time - deadline)
                    task.rank = int((100000 * (10000*priority))/slack)
            else:
                if((deadline - (min_time)) >= 0):
                    slack = 1 + (deadline - (min_time))
                    task.rank = int((100000 * (10*priority))/slack)                        
                else:
                    slack = 1 - 0.99/( min_time - deadline)
                    task.rank = int((100000 * (100*priority))/slack)
        else:
            slack = 1 + (deadline - (max_time))
            task.rank = int((100000 * (priority))/slack)


        # logging.info("Task rank: %d,%d,%d,%d,%d" % (task.rank, priority, deadline, sum, (len(stomp.servers) - none)))

    def dropping_policy(self, dag, task_node): 
        ex_time = max_length(dag.graph, task_node) #BCET of critical path
        if(dag.slack - ex_time < 0 and dag.priority == 1):

            dag.dropped = 1
            return True
        
        return False
           