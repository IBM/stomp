# Generates cost matrices based on given number of nodes and processors

# Copyright (C) 2017 RW Bunney

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.  

import os
import networkx as nx
import argparse
import random
import random
import os
import sys, getopt
import importlib
import json
import collections
import numpy

import networkx as nx
#from graph.graph import random_comp_matrix, random_comm_matrix, random_task_dag
output_file = '/home/aporvaa/research/IBM/inputs/'

class Task(object):

    def __init__(self, tid, comp_cost=[]):
        self.tid = int(tid)# task id - this is unique
        self.rank = -1 # This is updated during the 'Task Prioritisation' phase 
        self.processor = -1
        self.ast = 0 
        self.aft = 0 

    def __repr__(self):
        return str(self.tid)
    """
    To utilise the NetworkX graph library, we need to make the node structure hashable  
    Implementation adapted from: http://stackoverflow.com/a/12076539        
    """

    def __hash__(self):
        return hash(self.tid)

    def __eq__(self, task):
        if isinstance(task, self.__class__):
            return self.tid == task.tid
        return NotImplemented

    
    def __lt__(self,task): 
        if isinstance(task,self.__class__):
            return self.tid < task.tid

    def __le__(self,task):
        if isinstance(task,self.__class__):
            return self.tid <= task.tid

def random_comp_matrix(processors, nodes, lower,upper):
    """
    Function that generates a random cost matrix for a number of tasks
    
    :param processors: Number of processors available
    :param nodes: Number of nodes with costs
    :param cost: A range that determines the maximum random cost that can be generated
    """
    
    # For each processor, we have a list of nodes with computation/communication costs 
    conf_file = "/home/aporvaa/research/IBM/meta-stomp-gold/stomp.json"   
    stomp_params = {}
    with open(conf_file) as conf_file:
        params = json.load(conf_file)

    params['simulation']['servers'] = ["cpu_core","gpu","fft_accel"]
    STDEV_FACTOR = [0.01] #, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]  # percentages

    for stdev_factor in STDEV_FACTOR:

        computation_matrix = dict()

        name = (output_file + 'random_comp_{1}_{2}.txt').format(upper,nodes,stdev_factor)#,processors)    
        print(name)
        file = open(name,'w')
        file.write("type,P1,P2,...,Pn\n") 

        task_list = []
        for task_type in params['simulation']['tasks']:
            task_list.append(task_type)
            # if (task_type.startswith(fft)):
            #     fft_list.append(task_type)
            # elif (task_type.startswith(cnn)):
            #     cnn_list.append(task_type)
            # else
            #     task_list.append(task_type)
        tasks = []
        
        if(nodes == 5):
            #tasks = ['fft', 'cnn', 'decoder', 'cnn', 'decoder']
            tasks = numpy.random.choice(task_list, 5)
        elif(nodes == 7):
            #tasks = ['decoder', 'cnn', 'decoder', 'fft', 'cnn', 'fft', 'cnn', 'decoder', 'cnn', 'fft']
            tasks = numpy.random.choice(task_list, 7)
        elif(nodes == 10):
            #tasks = ['cnn', 'fft', 'cnn', 'fft', 'decoder', 'cnn', 'decoder']
            tasks = numpy.random.choice(task_list, 10)
        print(nodes)
        print(tasks)
        print("Done")

        for x in range(nodes):
            mat_entry = []
            # mat_entry.append(random.choice(['fft','decode
            # task = numpy.random.choice(list(params['simulation']['tasks'])) #type = random.choice(['fft','decoder','cnn'])
            task = tasks[x]
            mat_entry.append(task)
            # computation_matrix[x] = random.sample(range(lower,upper),processors)
            for server_type in params['simulation']['servers']:
                # print(server_type)
                if (server_type in params['simulation']['tasks'][task]['mean_service_time']):
                    mean_service_time  = params['simulation']['tasks'][task]['mean_service_time'][server_type]
                    stdev_service_time = params['simulation']['tasks'][task]['mean_service_time'][server_type]*stdev_factor
                    service_time = str(int(numpy.random.normal(loc=mean_service_time, scale=stdev_service_time, size=1)))
                    if (int(service_time) <= 0):
                        service_time = str(1)
                    mat_entry.append(service_time)
                else :
                    mat_entry.append(str(None))
            computation_matrix[x] = mat_entry
            # print(computation_matrix[x])
            s = ",".join(map(str,computation_matrix[x]))
            file.write(s +'\n')
    




    # for n in range(len(computation_matrix)):
    #     s = ", ".join(map(str,computation_matrix[n]))
    #     type = random.choice(['fft','decoder','cnn'])
    #     file.write(type +', ' + s +'\n')
    file.close()

    
    return computation_matrix

def random_comm_matrix(nodes, lower, upper):
    """
    Function that generates a random communication cost (n x n) matrix for a number of tasks
    
    :param nodes: Number of nodes with costs
    :param cost: A range that determines the maximum random cost that can be generated
    """
    
    # For each processor, we have a list of nodes with communication costs 
    #communication_matrix = dict()
    communication_matrix = [[0 for x in range(nodes)] for x in range(nodes)] 
    for x in range(nodes-1):
        for y in range(x+1,nodes):
            communication_matrix[x][y]=random.randint(lower,upper)
            communication_matrix[y][x]=communication_matrix[x][y]
            # print (communication_matrix[x][y])
    if not os.path.isdir((output_file + 'comm_{0}/').format(upper)):
        os.makedirs((output_file + 'comm_{0}/').format(upper))
    name = (output_file + 'comm_{0}/comm_{1}.txt').format(upper,nodes)    
    file = open(name,'w')
    file.write("N1,N2,...,Nx\n") 
    for n in range(len(communication_matrix)):
        file.write(str(communication_matrix[n])+'\n')
    file.close()

    return communication_matrix

def random_task_dag(nodes, edges):
    """Generate a random Directed Acyclic Graph (DAG) with a given number of nodes and edges.
    Modified from source: http://ipyparallel.readthedocs.io/en/latest/dag_dependencies.html
    """
    graph = nx.DiGraph()
    count = 0
    parent_nodes = []
    
    if nodes is 1:
        return graph
    for i in range(nodes):
        graph.add_node(Task(i))
    graph.add_edge(Task(0), Task(1))
    while edges > 0:
        a = Task(random.randint(0,nodes-1))
        b=a
        while b.tid==a.tid:
            b = Task(random.randint(1,nodes-1))
        if b.tid > 0 and a.tid >=0 :
            graph.add_edge(a,b)
            if nx.is_directed_acyclic_graph(graph):
                edges -= 1
            else:
                # we closed a loop!
                graph.remove_edge(a,b)
        else:
            continue

    node_list = graph.nodes()
    count = 1
    for node in node_list:
        if node.tid != 0:
            predecessors = graph.predecessors(node)
            while predecessors is []:
                new_task = random.randint(1,nodes-1)
                print("Addign edge")
                graph.add_edge(new_task,node)
                if  nx.is_directed_acyclic_graph(graph):
                    predecessors = graph.predecessors(node)     
                else:
                    print("remove edge")
                    graph.remove_edge(new_task,node)
        else:
            continue


    for n,d in graph.in_degree():
        if d == 0:
            if n.tid != 0:
                parent_nodes.append(n)
            else:
                root_node = n

    for n in parent_nodes:
        graph.add_edge(root_node,n)


    # print("Writing out graph")  
    nx.write_graphml(graph, (output_file + "random_dag_{0}.graphml").format(nodes))#,edges))

    return graph




# nodes = 1000;
# processors = 16;

# generates comp matrices
# for x in range(0,nodes):
#   # for y in range(1,5000): 
#           # random_comp_matrix(x,y,50) 
#   random_comm_matrix(nodes,200,500)   


# location = '/home/aporvaa/research/IBM/inputs/'
graphs = [] 

def generate_cost_matrix(comp_cost_min,comp_cost_max,comm_cost_min,comm_cost_max):
    # for val in os.listdir(location):
    #     graphs.append(location+val)

    for path in graphs:
        print ("Path: " + str(path))
        graph = nx.read_graphml(path,Task)
        num_nodes= len(graph.nodes())

        if num_nodes > 5000:
            continue

        for x in range(3,4):
            random_comp_matrix(x,num_nodes,comp_cost_min,comp_cost_max)
            # random_comm_matrix(num_nodes,comm_cost_min,comm_cost_max) 


if __name__ == '__main__':
    print("Hello")
    parser = argparse.ArgumentParser()
    parser.add_argument("--processor", help="number of processors")
    parser.add_argument("--min_comp",help="maximum communication cost")
    parser.add_argument("--max_comp",help="maximum computation cost")
    parser.add_argument("--min_comm",help="maximum communication cost")
    parser.add_argument("--max_comm",help="maximum computation cost")

    args = parser.parse_args()
    num_processors = 2
    min_comm = 0
    max_comm = 50
    
    min_comp=0
    max_comp = 50 

    if args.min_comp:
        min_comp = int(args.min_comp)
        print("Minimum communication cost: {0}".format(args.min_comp))

    if args.max_comp:
        max_comp= int(args.max_comp)
        print("Maximum communication cost: {0}".format(args.max_comp))

    if args.min_comm:   
        min_comm = int(args.max_comm)
        print("Maximum computation cost: {0}".format(args.max_comm))    
    
    if args.max_comm:
        max_comm = int(args.max_comm)
        print("Maximum communication cost: {0}".format(args.max_comm))
    
    if not os.path.isdir(output_file):
        os.makedirs(output_file)
        print("Creating outputdir" + output_file)
    
    
    random_task_dag(5,5)
    random_task_dag(10,10)
    #random_task_dag(7,7)

    graphs.append(output_file + "random_dag_5.graphml")
    graphs.append(output_file + "random_dag_10.graphml")
    #graphs.append(output_file + "random_dag_7.graphml")

    generate_cost_matrix(min_comp,max_comp, min_comm,max_comm)

    # G=nx.gnp_random_graph(10,0.5,directed=True)

    # DAG = nx.DiGraph([(u,v,) for (u,v) in G.edges() if u<v])

    # for n,d in DAG.in_degree():
    #         if(d == 0 and n != 0):
    #             DAG.add_edge(0,n)

    # for n,d in DAG.in_degree():
    #     print (str(n) + "," + str(d))
    #     if(d == 0):
    #         print("Parent node:" + str(n))
                

    # if (nx.is_directed_acyclic_graph(DAG)):
    #     nx.write_graphml(DAG, "DAG.graphml")
    
    # num_params(num_processors,max_comm_num,max_comp_num)


# 771, 108,1202,135,3,19603,3467,1095,7719,12498,3271,29227,2899,1615,4583,2068
