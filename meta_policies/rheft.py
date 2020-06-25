
from meta import BaseMetaPolicy

class PolicyVariables:
    def __init__(self, R_its_k_heft, ftsched):
        self.ftsched = ftsched
        self.R_its_k_heft = R_its_k_heft


class MetaPolicy(BaseMetaPolicy):

    def init(self, dag_types):
        self.pre_schd_data = {}
        for dag_type in dag_types:
            self.pre_schd_data[dag_type]=[]
            with open("pre_schd/random_"+ dag_type, 'r') as input_data:
                for line in input_data.readlines():
                #   print(line)
                    temp = line.strip().split(' ')
                    self.pre_schd_data[dag_type].append(temp)

    def set_policy_variables(self, dag):

        ## calculate sub dealine
        graph = dag.graph
        deadline = dag.deadline
        dag_type = dag.dag_type
        data = self.pre_schd_data[dag_type]
        
        max_v = 0
        for node in graph.nodes():
            #print(node.tid,data[node.tid][0])
            node.est = int(data[node.tid][1])
            node.eft = int(data[node.tid][2]) + node.est
            node.subD = deadline - node.est
            node.lst = deadline - node.eft
            if max_v < node.eft:
                max_v = node.eft 

        return PolicyVariables(0.31, max_v)


    def meta_static_rank(self, stomp, dag):
        graph = dag.graph
        comp = dag.comp

        ## rHEFT Rank
        size = len(comp)

        parents= [-1]*size
        order = []
        while size > 0: 

            for node in graph.nodes():
                parent_rank_comp =True
                parent_rank = [0]
                p=[]
                for parent in graph.predecessors(node):
                    parent_rank.append(parents[parent.tid])
                    if parents[parent.tid]== -1:
                        parent_rank_comp = False
                    p.append(parent.tid)

                if parent_rank_comp ==True:
                    if node.rank ==-1:         
                        size -=1
                        sum=0
                        none = 0
                        for server in stomp.servers:
                            if server.type == "cpu_core":
                                sum+=int(comp[node.tid][2])
                            if server.type == "gpu":
                                sum+=int(comp[node.tid][3])
                            if server.type == "fft_accel":
                                if comp[node.tid][4]=="None":
                                    none+=1
                                else:
                                    sum+=int(comp[node.tid][4])

                        node.rank = sum/(len(stomp.servers)-none) + max(parent_rank)       
                        parents[node.tid] = node.rank


    def meta_dynamic_rank(self, stomp, task, comp, max_time, min_time, deadline, priority):
        pass  

    def dropping_policy(self, dag, task_node):  
        pass   