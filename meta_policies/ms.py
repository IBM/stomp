
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

        sum=0
        none = 0
        for server in stomp.servers:
            if server.type == "cpu_core":
                sum+=int(comp[task.tid][2])
            if server.type == "gpu":
                sum+=int(comp[task.tid][3])
            if server.type == "fft_accel":
                if comp[task.tid][4]=="None":
                    none+=1
                else:
                    sum+=int(comp[task.tid][4])



        if ((deadline - (sum/(len(stomp.servers) - none))) == 0):
            slack = 1
        else:
            if ((deadline - (sum/(len(stomp.servers) - none))) < 0):
                slack = 1/((sum/(len(stomp.servers) - none)) - deadline)
            else:
                slack = 1 + (deadline - (sum/(len(stomp.servers) - none)))

        if ((deadline - (max_time)) == 0):
            slack_max = 1
        else:
            if ((deadline - (max_time)) < 0):
                slack_max = 1/((max_time) - deadline)
            else:
                slack_max = 1 + (deadline - (max_time))
        
        task.rank = int(100000 * ((priority)/slack_max))
        # logging.info("Task rank: %d,%d,%d,%d,%d" % (task.rank, priority, deadline, sum, (len(stomp.servers) - none)))

    def dropping_policy(self, dag, task_node): 
        ex_time = max_length(dag.graph, task_node)
        if(dag.slack - ex_time < 0 and dag.priority == 1):

            dag.dropped = 1
            return True
        
        return False
           