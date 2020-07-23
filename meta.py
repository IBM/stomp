from __future__ import division
from __future__ import print_function
from abc import ABCMeta, abstractmethod
import numpy
import pprint
import sys
import operator
import logging
from datetime import datetime, timedelta

import time
import networkx as nx
from csv import reader

def read_matrix(matrix):
    lmatrix = []
    f = open(matrix)
    next(f)
    csv_reader = reader(f)
    for row in csv_reader:
        # logging.info(row)
        lmatrix.append(list(map(str,row)))
    f.close()
    return lmatrix

def max_length(G, node_run):
    leaf_nodes = [node for node in G.nodes() if G.out_degree(node)==0]
    time_dict = nx.get_node_attributes(G, 't')

    max_path_length = 0
    num_paths = 0

    for leaf in leaf_nodes:
        for path in nx.all_simple_paths(G, source=node_run, target=leaf):
            sum = 0
            for key in path:
                sum += int(time_dict[key])

            if (sum > max_path_length):
                max_path_length = sum
            num_paths += 1
    if(num_paths == 0):
        min_time = int(time_dict[node])
        return min_time

    return max_path_length

###############################################################################
# This class represents a 'task' that is processed in the queuing system.     #                                           #
###############################################################################
class TASK:

    def __init__(self, tid):

        self.tid                        = int(tid)# task id - this is unique
        self.dag_id                     = None
        self.scheduled                  = 0
        self.rank                       = -1
        self.processor                  = -1

    def init_task(self, arrival_time, dag_id, tid, type, params, priority, deadline, dag_dtime):
        self.dag_id                     = dag_id
        self.tid                        = tid
        self.type                       = type  # The task type
        self.priority                   = priority  # Task input priority
        self.deadline                   = deadline  # Task input deadline
        self.dtime                      = dag_dtime
        self.mean_service_time_dict     = params['mean_service_time']
        self.mean_service_time_list     = sorted(params['mean_service_time'].items(), key=operator.itemgetter(1))
        self.stdev_service_time_dict    = params['stdev_service_time']
        self.stdev_service_time_list    = sorted(params['stdev_service_time'].items(), key=operator.itemgetter(1))
        self.arrival_time               = arrival_time
        self.noaffinity_time            = 0
        self.departure_time             = None
        self.per_server_services        = []    # Holds ordered list of service times
        self.per_server_service_dict    = {}    # Holds (server_type : service_time) key-value pairs; same content as services list really
        self.task_service_time          = None  # To be set upon scheduling, since it depends on the target server
        self.task_lifetime              = None  # To be set upon finishing; includes time span from arrival to departure
        self.trace_id                   = None
        self.wpower                     = None
        self.current_time               = 0
        self.possible_server_idx        = None
        self.possible_mean_service_time = None
        self.peid                       = None
        self.parent_data                = []
        self.server_type                = None
        self.ptoks_used                 = None  # Power consumed during actual execution on servers[server_type]
        self.power_dict                 = params['power']
        self.rank_type                  = 0

        self.reserved_server_id         = None

    def calc_slack(self, sim_time, service_time, remaining_time):
        # print("[%10u][%u.%u] Deadline: %u" % (sim_time, self.dag_id, self.tid, self.arrival_time + self.deadline))
        wait_time = sim_time - self.arrival_time
        actual_time = service_time + remaining_time
        return self.deadline - wait_time - actual_time

    def __str__(self):
        return ('Task ' + str(self.trace_id) + ' ( ' + self.type + ' ) ' + str(self.arrival_time))

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
            return (self.tid == task.tid and self.dag_id == task.dag_id)
        return NotImplemented


    def __lt__(self,task):
        if isinstance(task,self.__class__):
            return self.tid < task.tid

    def __le__(self,task):
        if isinstance(task,self.__class__):
            return self.tid <= task.tid

class DAG:
    def __init__(self, graph, comp, parent_dict, atime, deadline, dtime, priority, dag_type):


        self.graph              = graph
        self.comp               = comp
        self.parent_dict        = parent_dict
        self.arrival_time       = atime
        self.deadline           = deadline
        self.dtime              = dtime
        self.resp_time          = 0
        self.slack              = deadline
        self.priority           = priority
        self.ready_time         = atime
        self.dag_type           = dag_type
        self.dropped            = 0
        self.completed_peid     = {}
        self.noaffinity_time    = 0
        # logging.info("Created %d,%d" % (self.arrival_time,self.deadline))
        self.energy         = 0

class BaseMetaPolicy:

    __metaclass__ = ABCMeta

    @abstractmethod
    def init(self): pass

    @abstractmethod
    def set_task_variables(self, dag, task_node): pass

    @abstractmethod
    def set_dag_variables(self, dag): pass

    @abstractmethod
    def meta_static_rank(self, stomp, dag): pass

    @abstractmethod
    def meta_dynamic_rank(self, stomp, task, comp, max_time, min_time, deadline): pass

    @abstractmethod
    def dropping_policy(self, dag, task_node): pass


class META:

    E_PWR_MGMT          = 1
    E_TASK_ARRIVAL      = 2
    E_SERVER_FINISHES   = 3
    E_NOTHING           = 4

    E_META_DONE         = 0

    def __init__(self, meta_params, stomp_sim, meta_policy):

        self.params         = meta_params
        self.stomp          = stomp_sim
        self.meta_policy    = meta_policy

        self.working_dir    = self.params['general']['working_dir']
        self.basename       = self.params['general']['basename']

        self.dag_trace_files                = {}
        self.output_trace_file              = self.params['general']['output_trace_file']
        self.input_trace_file               = self.params['general']['input_trace_file'][1]
        self.stdev_factor                   = self.params['simulation']['stdev_factor']

        self.global_task_trace              = []

        self.dag_dict                       = {}
        self.dag_id_list                    = []
        self.server_types                   = ["cpu_core", "gpu", "fft_accel"]

    def run(self):

        self.meta_policy.init(self.params["simulation"]["dag_types"])

        ### Read input DAGs ####
        dags_completed = 0
        dags_completed_per_interval = 0
        end_list = []
        dropped_list = []
        time_interval = 0
        last_promoted_id = 0
        promote_interval = 10*self.params['simulation']['arrival_time_scale']*self.params['simulation']['mean_arrival_time']
        in_trace_name = self.working_dir + '/' + self.input_trace_file
        logging.info(in_trace_name)
        # print("inputs/random_comp_5_{1}.txt".format(5, self.stdev_factor))

        while(self.stomp.E_TSCHED_START == 0):
            pass

        ## Read trace file and populate DAG information ##
        # self.stomp.dlock.acquire()
        with open(in_trace_name, 'r') as input_trace:
            line_count = 0;
            for line in input_trace.readlines():
                tmp = line.strip().split(',')
                if (line_count >= 0):
                    atime = int(int(tmp.pop(0))*self.params['simulation']['arrival_time_scale'])
                    dag_id = int(tmp.pop(0))
                    dag_type = tmp.pop(0)
                    graph = nx.read_graphml("inputs/random_dag_{0}.graphml".format(dag_type), TASK)

                    #### AFFINITY ####
                    # Add matrix to maintain parent node id's
                    ####
                    parent_dict = {}
                    for node in graph.nodes():
                        parent_list = []
                        for pred_node in graph.predecessors(node):
                            parent_list.append(pred_node.tid)
                        parent_dict[node.tid] = parent_list
                        # logging.info(str(node.tid) + ": " + str(parent_dict[node.tid]))
                    comp = read_matrix("inputs/random_comp_{0}_{1}.txt".format(dag_type, self.stdev_factor))
                    # if (self.params['simulation']['policy'].startswith("ms3")):
                    #     comp = read_matrix("inputs/random_comp_{0}_{1}_slack.txt".format(dag_type, self.stdev_factor))
                    priority = int(tmp.pop(0))
                    deadline = int(tmp.pop(0))*(self.params['simulation']['arrival_time_scale']*self.params['simulation']['deadline_scale'])
                    dtime = atime + deadline



                    the_dag_trace = DAG(graph, comp, parent_dict, atime, deadline, dtime, priority, dag_type)
                    the_dag_trace.dag_variables = self.meta_policy.set_dag_variables(the_dag_trace)
                    self.dag_dict[dag_id] = the_dag_trace
                    self.dag_id_list.append(dag_id)

                    ## Static ranking ##
                    self.meta_policy.meta_static_rank(self.stomp, the_dag_trace)

            line_count += 1
        # self.stomp.dlock.release()
        ctime = timedelta(microseconds = 0)
        rtime = timedelta(microseconds = 0)


        while(self.dag_id_list or self.stomp.E_TSCHED_DONE == 0):
            temp_task_trace = []
            completed_list = []
            dropped_dag_id_list = []

            ## Get Completed Tasks from TSCHED ##
            self.stomp.tlock.acquire()
            while(len(self.stomp.tasks_completed)):
                completed_list.append(self.stomp.tasks_completed.pop(0))
            self.stomp.tlock.release()

            ## Update DAGs and meta info for completed tasks ##
            start = datetime.now()
            while (len(completed_list)):
                task_completed = completed_list.pop(0)
                dag_id_completed = task_completed.dag_id

                ## If the task belongs to a non-dropped DAG ##
                if dag_id_completed in self.dag_dict:
                    dag_completed = self.dag_dict[dag_id_completed]
                    # logging.info('[%10d]Task completed : %d,%d,%d' % (self.stomp.sim_time,(task_completed.arrival_time + task_completed.task_lifetime),dag_id_completed,task_completed.tid))

                    ## Remove completed task from parent DAG and update meta-info ##
                    for node in dag_completed.graph.nodes():
                        if node.tid == task_completed.tid:
                            # TODO: If internal task deadline of priority == 1 is not met drop it
                            dag_completed.ready_time = task_completed.arrival_time + task_completed.task_lifetime
                            dag_completed.resp_time = dag_completed.ready_time - dag_completed.arrival_time
                            dag_completed.slack = dag_completed.deadline - dag_completed.resp_time
                            #### AFFINITY ####
                            # Add completed id and HW id to a table
                            ####
                            dag_completed.completed_peid[task_completed.tid] = task_completed.peid
                            dag_completed.noaffinity_time += task_completed.noaffinity_time

                            # print("Completed: %d,%d,%d,%d,%d,%d" % (dag_id_completed,task_completed.tid,dag_completed.slack,dag_completed.deadline,task_completed.arrival_time,task_completed.task_lifetime))

                            task = task_completed.type
                            assert task_completed.ptoks_used
                            # power = self.params['simulation']['tasks'][task]['power'][task_completed.server_type]
                            #print(task,power,task_completed.task_lifetime)
                            dag_completed.energy += task_completed.task_service_time * \
                                    task_completed.ptoks_used
                            # print('[%d.%d] task %s | task_service_time %u |  ptoks_used : %u | energy = %u | dag accum energy %u' % 
                            #     (task_completed.dag_id, task_completed.tid, task_completed.type, task_completed.task_service_time, task_completed.ptoks_used, task_completed.task_service_time * task_completed.ptoks_used, dag_completed.energy))

                            dag_completed.graph.remove_node(node)
                            break;


                    ## Update stats if DAG has finished execution ##
                    # self.stomp.dlock.acquire()
                    if (len(dag_completed.graph.nodes()) == 0):
                        dags_completed += 1
                        # logging.info("%d: DAG id: %d completed" %(self.stomp.sim_time, dag_id_completed))
                        if(dag_completed.priority == 1 and dag_id_completed >= last_promoted_id):
                            # print("[%d]: Completed DAG id: %d priority: %d" %(self.stomp.sim_time, dag_id_completed, dag_completed.priority))
                            dags_completed_per_interval += 1
                        ## Calculate stats for the DAG
                        # logging.info(str(self.params['simulation']['sched_policy_module'].split('.')[-1].split('_')[-1]) + ',' + str(dag_id_completed) + ',' + str(dag_completed.priority) + ',' +str(dag_completed.slack))
                        # logging.info(str(dag_id_completed) + ',' + str(dag_completed.priority) + ',' +str(dag_completed.slack))
                        end_entry = (dag_id_completed,dag_completed.priority,dag_completed.dag_type,dag_completed.slack, dag_completed.resp_time, dag_completed.noaffinity_time,dag_completed.energy)
                        end_list.append(end_entry)
                        # Remove DAG from active list
                        self.dag_id_list.remove(dag_id_completed)
                        del self.dag_dict[dag_id_completed]
                    # self.stomp.dlock.release()
            end = datetime.now()
            ctime += end - start


            start = datetime.now()

            # Check for DAGs to be dropped
            if(self.params['simulation']['drop'] == True):
                for dag_id in self.dag_id_list:
                    the_dag_sched = self.dag_dict[dag_id]

                    if dag_id in self.stomp.drop_hint_list and the_dag_sched.priority == 1:
                        # print("[ID: %d]Dropping based on hint from task scheduler" %(dag_id))
                        dropped_entry = (dag_id,the_dag_sched.priority,the_dag_sched.dag_type,the_dag_sched.slack, the_dag_sched.resp_time, the_dag_sched.noaffinity_time)
                        self.stomp.dags_dropped.append(dag_id)
                        dropped_list.append(dropped_entry)
                        dropped_dag_id_list.append(dag_id)
                        continue

                    for node,deg in the_dag_sched.graph.in_degree():
                        if deg == 0:
                            ##### DROPPED ##########
                            # TODO: Fix this code to be non-deterministic
                            # if(self.params['simulation']['drop'] == True):
                            #     if(the_dag_sched.priority == 1 and (the_dag_sched.dtime - self.stomp.sim_time) < 0):
                            #         the_dag_sched.dropped = 1
                            #         dropped_entry = (dag_id,the_dag_sched.priority,the_dag_sched.dag_type,the_dag_sched.slack, the_dag_sched.resp_time, the_dag_sched.noaffinity_time)
                            #         self.stomp.dags_dropped.append(dag_id)
                            #         dropped_list.append(dropped_entry)
                            #         dropped_dag_id_list.append(dag_id)
                            #         break

                            if node.scheduled == 0:
                                if(self.meta_policy.dropping_policy(the_dag_sched, node)):
                                    # logging.info("%d: [DROPPED] DAG id: %d dropped" %(self.stomp.sim_time, dag_id))
                                    dropped_entry = (dag_id,the_dag_sched.priority,the_dag_sched.dag_type,the_dag_sched.slack, the_dag_sched.resp_time, the_dag_sched.noaffinity_time)
                                    self.stomp.dags_dropped.append(dag_id)
                                    dropped_list.append(dropped_entry)
                                    dropped_dag_id_list.append(dag_id)
                                    break

                # Remove Dropped DAGs from active DAG list
                # self.stomp.dlock.acquire()
                for dag_id_dropped in dropped_dag_id_list:
                    self.dag_id_list.remove(dag_id_dropped)
                    del self.dag_dict[dag_id_dropped]
                # self.stomp.dlock.release()


            ## Check for ready tasks ##
            for dag_id in self.dag_id_list:
                the_dag_sched = self.dag_dict[dag_id]

                ## Push ready tasks into ready queue ##
                for task_node,deg in the_dag_sched.graph.in_degree():
                    if deg == 0:

                        # #### DROPPED ##########
                        # if(self.params['simulation']['drop'] == True):
                        #     if(self.meta_policy.dropping_policy(the_dag_sched, task_node)):
                        #         dropped_entry = (dag_id,the_dag_sched.priority,the_dag_sched.dag_type,the_dag_sched.slack, the_dag_sched.resp_time, the_dag_sched.noaffinity_time)
                        #         self.stomp.dags_dropped.append(dag_id)
                        #         dropped_list.append(dropped_entry)
                        #         dropped_dag_id_list.append(dag_id)
                        #         break

                        ## PROMOTE DAGs
                        # if(self.params['simulation']['promote'] == True):
                        #     if (the_dag_sched.arrival_time > time_interval + promote_interval and the_dag_sched.priority == 1 and task_node.tid == 0 and task_node in self.stomp.tasks):
                        #         # print("[%d]: [%d.%d.%d], atime: %d, time_threshold: %d, completed: %d\n" % (self.stomp.sim_time, dag_id, task_node.tid, the_dag_sched.priority, the_dag_sched.arrival_time, (time_interval + promote_interval), dags_completed_per_interval))
                        #         # print("[%d]: DAG id: %d, atime: %d, completed DAGs: %d\n" % (self.stomp.sim_time, dag_id, the_dag_sched.arrival_time, dags_completed_per_interval))
                        #         if dags_completed_per_interval <= 0:
                        #             task_node.priority = 3
                        #             the_dag_sched.priority = 3
                        #             print("%d: [%d]Dag promoted\n" %(self.stomp.sim_time, dag_id))
                        #         dags_completed_per_interval = 0
                        #         time_interval = the_dag_sched.arrival_time
                        #         last_promoted_id = dag_id



                        if task_node.scheduled == 0:
                            if (task_node.tid == 0):
                                atime = the_dag_sched.arrival_time
                            else:
                                atime = the_dag_sched.ready_time
                            task_type = the_dag_sched.comp[task_node.tid][0]
                            priority = the_dag_sched.priority
                            deadline = int(the_dag_sched.slack)

                            #Use SDR for task deadline calculation
                            if (self.params['simulation']['policy'].startswith("ms1")):
                                deadline = int(the_dag_sched.deadline*float(the_dag_sched.comp[task_node.tid][1]))
                            if (self.params['simulation']['policy'].startswith("ms3")):
                                deadline = int(deadline*float(the_dag_sched.comp[task_node.tid][1]))


                            # Initialize task during execution
                            task_node.init_task(atime, dag_id, task_node.tid, task_type, self.params['simulation']['tasks'][task_type], priority, deadline, int(the_dag_sched.dtime))

                            # Set task variables specific to the policy
                            task_node.task_variables = self.meta_policy.set_task_variables(the_dag_sched, task_node)

                            ## Update service_time of task on all servers
                            stimes = []
                            count = 0
                            max_time = 0
                            min_time = 100000
                            # Iterate over each column of comp entry.
                            for service_time in the_dag_sched.comp[task_node.tid]:
                                # Ignore first two columns.
                                if (count <= 1):
                                    count += 1
                                    continue
                                else:
                                    task_node.per_server_services.append(service_time)
                                    if (service_time != "None"):
                                        ## Warning; If number of entries in comp file changes, this needs to change
                                        server_type = self.server_types[count-2]
                                        task_node.per_server_service_dict[server_type] = round(float(service_time))
                                        # print(str(server_type + "," + str(service_time))

                                        # Min and max service time calculation
                                        if (min_time > round(float(service_time))):
                                            min_time = round(float(service_time))
                                        if(max_time < float(service_time)):
                                            max_time = float(service_time)

                                count += 1

                            # Dynamic Rank Assignment
                            self.meta_policy.meta_dynamic_rank(self.stomp, task_node, the_dag_sched.comp, max_time, min_time, deadline, priority)


                            #### AFFINITY ####
                            # Pass parent id and HW id of parents with task
                            ####
                            parent_data = []
                            for parent in the_dag_sched.parent_dict[task_node.tid]:
                                parent_data.append((parent,the_dag_sched.completed_peid[parent]))
                            task_node.parent_data = parent_data

                            ## Ready task found, push into temp ready task queue
                            temp_task_trace.append(task_node)
                            task_node.scheduled = 1

            end = datetime.now()
            rtime += end - start

            self.stomp.lock.acquire()
            ## Push all ready tasks in the order of their arrival time ##
            while (len(temp_task_trace)):
                # logging.info('Inserting : %d,DAG:%d,TID:%d' % (temp_task_trace[0].arrival_time,temp_task_trace[0].dag_id,temp_task_trace[0].tid))
                self.stomp.global_task_trace.append(temp_task_trace.pop(0))
                self.stomp.global_task_trace.sort(key=lambda tr_entry: tr_entry.arrival_time, reverse=False)

            if (len(self.stomp.global_task_trace) and (self.stomp.next_cust_arrival_time != self.stomp.global_task_trace[0].arrival_time)):
                self.stomp.next_cust_arrival_time = self.stomp.global_task_trace[0].arrival_time

            self.stomp.tlock.acquire()
            if(self.stomp.task_completed_flag == 1 and (len(self.stomp.tasks_completed) == 0)):
                self.stomp.task_completed_flag = 0
            self.stomp.tlock.release()

            self.stomp.lock.release()

            ## Update META START after first iteration in META. Used to start TSCHED and STOMP processing
            self.stomp.E_META_START = 1
            self.stomp.stats['Tasks Generated by META'] = 1

            ## If all DAGs have completed update META is done
            if(len(self.dag_id_list) == 0):
                self.stomp.E_META_DONE = 1
                # logging.info("META completed")

        # Open output file and write DAG stats
        fho = open(self.params['general']['working_dir'] + '/run_stdout_' + self.params['general']['basename'] + '.out', 'w')
        fho.write("Dropped,DAG ID,DAG Priority,DAG Type,Slack,Response Time,No-Affinity Time,Energy\n")

        end_list.sort(key=lambda end_entry: end_entry[0], reverse=False)
        while(len(end_list)):
            end_entry = end_list.pop(0)
            fho.write("0," + str(end_entry[0]) + ',' + str(end_entry[1]) + ',' + str(end_entry[2]) + ',' + str(end_entry[3]) + ',' + str(end_entry[4]) + ',' + str(end_entry[5]) + ',' + str(end_entry[6]) + '\n')
            # end_entry = (dag_id_completed,dag_completed.priority,dag_completed.dag_type,dag_completed.slack, dag_completed.resp_time, dag_completed.noaffinity_time)

        dropped_list.sort(key=lambda dropped_entry: dropped_entry[0], reverse=False)
        while(len(dropped_list)):
            dropped_entry = dropped_list.pop(0)
            fho.write("1," + str(dropped_entry[0]) + ',' + str(dropped_entry[1]) + ',' + str(dropped_entry[2]) + ',' + str(dropped_entry[3]) + ',' + str(dropped_entry[4]) + ',' + str(dropped_entry[5])  + ',' + str(end_entry[6]) + '\n')

        #(Processing time for completed task, ready task time, task assignment, task ordering)
        fho.write(("Time: %d, %d, %d, %d\n")%(ctime.microseconds, rtime.microseconds, self.stomp.ta_time.microseconds, self.stomp.to_time.microseconds))

        fho.close()
