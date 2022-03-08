
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

    def init(self, params):
        application = params['simulation']['application']
        dag_types = params["simulation"]['applications'][application]["dag_types"] 

        self.pre_schd_data = {}
        for dag_type in dag_types:
            self.pre_schd_data[dag_type]=[]
            pre_schd_file = "pre_schd/" + application + "_dag_" + dag_type
            with open(pre_schd_file, 'r') as input_data:
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
                        count = 0
                        i = 0
                        num_servers = 0
                        for service_time in comp[node.tid]:
                            # Ignore first two columns.
                            if (count <= 1):
                                count += 1
                                continue
                            else:
                                if (service_time != "None"):
                                    sum += round(float(service_time))
                                    num_servers += stomp.params['simulation']['servers'][stomp.server_types[i]]['count']
                                i += 1
                            count += 1  

                        node.rank = sum/(num_servers) + max(parent_rank)       
                        parents[node.tid] = node.rank

    def meta_dynamic_rank(self, stomp, task, comp, max_time, min_time, deadline, priority):
        pass  

    def dropping_policy(self, dag, task_node):  
        pass   
