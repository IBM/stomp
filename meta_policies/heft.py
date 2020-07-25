
from meta import BaseMetaPolicy

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
        graph = dag.graph
        comp = dag.comp
        size = len(graph.nodes())
        childs= [-1]*size

        while size > 0:
            for node in graph.nodes():

                child_rank_comp = True
                child_rank = [0]
                for child in graph.successors(node):
                    child_rank.append(childs[child.tid])
                    if childs[child.tid]== -1:
                        child_rank_comp = False    


                if child_rank_comp == True:
                    if node.rank ==-1:  
                        size -=1
                        sum=0
                        none = 0
                        count = 0
                        for service_time in comp[node.tid]:
                            # Ignore first two columns.
                            if (count <= 1):
                                count += 1
                                continue
                            else:
                                if (service_time != "None"):
                                    sum += round(float(service_time))
                                else:
                                    none += 1
                            count += 1  


                        node.rank = sum/(len(stomp.servers)-none) + max(child_rank)
                        childs[node.tid] = node.rank
                        # print("tid: %d, rank: %d" %(node.tid, node.rank))
                                    

    def meta_dynamic_rank(self, stomp, task, comp, max_time, min_time, deadline, priority):
        pass 

    def dropping_policy(self, dag, task_node): 
        pass      