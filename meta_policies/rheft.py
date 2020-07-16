
from meta import BaseMetaPolicy

class TaskVariables:
    def __init__(self, ftsched, R_its_k_heft, est, eft, subD, lst, rld):
        self.ftsched        = ftsched
        self.R_its_k_heft   = R_its_k_heft
        self.est            = est 
        self.eft            = eft 
        self.subD           = subD
        self.lst            = lst 
        self.rld            = rld 


class DAGVariables:
    def __init__(self, R_its_k_heft, ftsched):
        self.ftsched        = ftsched
        self.R_its_k_heft   = R_its_k_heft


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

    def set_dag_variables(self, dag):

        ## calculate sub dealine
        graph = dag.graph
        deadline = dag.deadline
        dag_type = dag.dag_type
        data = self.pre_schd_data[dag_type]
        
        max_v = 0
        for node in graph.nodes():
            #print(node.tid,data[node.tid][0])
            est = int(data[node.tid][1])
            eft = int(data[node.tid][2]) + est
            subD = deadline - est
            lst = deadline - eft
            if max_v < eft:
                max_v = eft 

        return DAGVariables(0.31, max_v)
   
    def set_task_variables(self, dag, task_node):

        ## calculate sub dealine
        graph = dag.graph
        deadline = dag.deadline
        dag_type = dag.dag_type
        data = self.pre_schd_data[dag_type]

        ftsched        = dag.dag_variables.ftsched
        R_its_k_heft   = dag.dag_variables.R_its_k_heft
        
        est = int(data[task_node.tid][1])
        eft = int(data[task_node.tid][2]) + est
        subD = deadline - est
        lst = deadline - eft
        rld = (lst - ftsched)/(eft)

        return TaskVariables(ftsched, R_its_k_heft, est, eft, subD, lst, rld)

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