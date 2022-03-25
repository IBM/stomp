#!/usr/bin/env python
#
# Copyright 2022 IBM
#
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#

from __future__ import division
from __future__ import print_function
from abc import ABCMeta, abstractmethod
import numpy
import pprint
import sys
import simpy
import operator
import logging
from datetime import datetime, timedelta
from tqdm import tqdm
import time
import networkx as nx
from csv import reader

from utils import message_decode_event, events, bcolors, handle_event

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
        min_time = int(time_dict[node_run])
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

    def init_task(self, arrival_time, dag_type, dag_id, tid, type, params, priority, deadline, dag_dtime):
        self.dag_type                   = dag_type
        self.dag_id                     = dag_id
        self.tid                        = tid
        self.type                       = type  # The task type
        self.priority                   = priority  # Task input priority
        self.deadline                   = deadline  # Task input deadline
        self.dtime                      = dag_dtime
        self.mean_service_time_dict     = params['mean_service_time']
        self.mean_service_time_list     = sorted(params['mean_service_time'].items(), key=operator.itemgetter(1))
        self.arrival_time               = arrival_time
        self.noaffinity_time            = 0
        self.departure_time             = None
        self.per_server_services        = []    # Holds ordered list of service times
        self.per_server_service_dict    = {}    # Holds (server_type : service_time) key-value pairs; same content as services list really
        self.max_time                   = None
        self.min_time                   = None
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
        return ('[{}.{}]'.format(self.dag_id, self.tid) + ' ( ' + self.type + ' ) ' + str(self.arrival_time))

    def __repr__(self):
        return self.__str__()
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
        self.promoted           = 0
        self.perm_promoted      = 0
        self.completed_peid     = {}
        self.noaffinity_time    = 0
        self.energy             = 0

class BaseMetaPolicy:

    __metaclass__ = ABCMeta

    @abstractmethod
    def init(self, params): pass

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

    class Profiler:
        def __init__(self):
            # Initialize profilers
            self.ctime     = timedelta(microseconds=0)
            self.rtime     = timedelta(microseconds=0)
            self.sranktime = timedelta(microseconds=0)
            self.dranktime = timedelta(microseconds=0)

    def __init__(self, sharedObjs, meta_params, stomp_sim, meta_policy):
        self.env               = sharedObjs.env
        self.max_timesteps     = sharedObjs.max_timesteps
        self.tsched_eventq     = sharedObjs.tsched_eventq
        self.meta_eventq       = sharedObjs.meta_eventq
        self.global_task_trace = sharedObjs.global_task_trace
        self.tasks_completed   = sharedObjs.tasks_completed
        self.dags_dropped      = sharedObjs.dags_dropped
        self.drop_hint_list    = sharedObjs.drop_hint_list

        self.profiler = self.Profiler()

        self.dags_completed = 0
        self.dags_completed_per_interval = 0

        # Cumulative energy for all tasks executed by the system
        self.all_tasks_energy = 0
        self.lt_wcet_r_crit = 0
        self.wtr_crit = 0
        self.tasks_completed_count_crit = 0

        self.lt_wcet_r_nocrit = 0
        self.wtr_nocrit = 0
        self.tasks_completed_count_nocrit = 0

        self.params         = meta_params
        self.stomp          = stomp_sim
        self.meta_policy    = meta_policy

        self.drop           = self.params['simulation']['drop']

        self.ticks_since_last_promote = 0
        self.last_promoted_dag_id = 0
        self.promote_interval = 100*self.params['simulation']['arrival_time_scale']*self.params['simulation']['mean_arrival_time']

        self.working_dir    = self.params['general']['working_dir']
        self.basename       = self.params['general']['basename']

        self.dag_trace_files                = {}
        self.output_trace_file              = self.params['general']['output_trace_file']
        self.input_trace_file               = self.params['general']['input_trace_file']

        self.dag_dict                       = {}
        self.dag_id_list                    = []
        self.server_types                   = []

        self.end_list = []
        self.dropped_list = []

        for type_count in range(0,len(self.params['simulation']['servers'])):
            for server_type in self.params['simulation']['servers']:
                if(self.params['simulation']['servers'][server_type]['id'] == type_count):
                    self.server_types.append(server_type)
                    break

        self.action = self.env.process(self.run())

    def print(self, string):
        pass
        #logging.info(bcolors.WARNING + "[%10ld][  META] " % self.env.now + str(string) + bcolors.ENDC)

    def handle_task_completion(self):
        if self.tasks_completed.empty():
            return
        task_completed = self.tasks_completed.get()
        # self.print("task_completed = {}".format(task_completed))
        dag_id_completed = task_completed.dag_id

        # Calculate energy per task and accumulate.
        self.all_tasks_energy += task_completed.task_service_time * task_completed.ptoks_used
        # print('[%d.%d.%d] task %s | task_service_time %u |  ptoks_used : %u | ENERGY = %u | cumulative energy %u' %
        #     (task_completed.dag_id, task_completed.tid, task_completed.priority,
        #         task_completed.type, task_completed.task_service_time, task_completed.ptoks_used,
        #         task_completed.task_service_time * task_completed.ptoks_used, all_tasks_energy))

        if task_completed.priority > 1:
            wait_time_crit = task_completed.task_lifetime - task_completed.task_service_time
            wcet_crit = task_completed.per_server_service_dict['cpu_core']

            self.lt_wcet_r_crit += (float)(task_completed.task_lifetime/wcet_crit)

            self.wtr_crit += (float)(wait_time_crit/task_completed.task_lifetime)
            self.tasks_completed_count_crit += 1
        else:
            wait_time_nocrit = task_completed.task_lifetime - task_completed.task_service_time
            wcet_nocrit = task_completed.per_server_service_dict['cpu_core']

            self.lt_wcet_r_nocrit += (float)(task_completed.task_lifetime/wcet_nocrit)

            self.wtr_nocrit += (float)(wait_time_nocrit/task_completed.task_lifetime)
            self.tasks_completed_count_nocrit += 1

        ## If the task belongs to a non-dropped DAG ##
        if dag_id_completed in self.dag_dict:
            dag_completed = self.dag_dict[dag_id_completed]
            # logging.info('[%10d]Task completed : %d,%d,%d' % (self.stomp.sim_time,(task_completed.arrival_time + task_completed.task_lifetime),dag_id_completed,task_completed.tid))

            ## Remove completed task from parent DAG and update meta-info ##
            for node in dag_completed.graph.nodes():
                if node.tid == task_completed.tid:
                    # TODO: If internal task deadline of priority == 1 is not met drop it
                    dag_completed.ready_time = task_completed.arrival_time + task_completed.task_lifetime
                    dag_completed.resp_time  = self.env.now - dag_completed.arrival_time
                    dag_completed.slack      = dag_completed.deadline - dag_completed.resp_time
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

                    dag_completed.graph.remove_node(node)
                    break

            ## Update stats if DAG has finished execution ##
            if not dag_completed.graph.nodes():
                self.dags_completed += 1
                # if self.dags_completed == 40:
                #     exit(1)
                # update progressbar
                self.pbar.update(n=1)

                # print(f"-- {self.dags_completed} DAGs completed")
                # print(f"tsched_eventq size = {self.tsched_eventq.qsize()}")
                # print(f"meta_eventq size = {self.meta_eventq.qsize()}")
                # print(f"global_task_trace size = {self.global_task_trace.qsize()}")
                # print(f"tasks_completed size = {self.tasks_completed.qsize()}")
                # print(f"dags_dropped size = {self.dags_dropped.qsize()}")
                # print(f"drop_hint_list size = {self.drop_hint_list.qsize()}")

                # logging.info("%d: DAG id: %d completed" %(self.stomp.sim_time, dag_id_completed))
                if(dag_completed.priority == 1 and dag_id_completed >= self.last_promoted_dag_id):
                    # print("[%d]: Completed DAG id: %d priority: %d" %(self.stomp.sim_time, dag_id_completed, dag_completed.priority))
                    self.dags_completed_per_interval += 1
                ## Calculate stats for the DAG
                # logging.info(str(self.params['simulation']['sched_policy_module'].split('.')[-1].split('_')[-1]) + ',' + str(dag_id_completed) + ',' + str(dag_completed.priority) + ',' +str(dag_completed.slack))
                # logging.info(str(dag_id_completed) + ',' + str(dag_completed.priority) + ',' +str(dag_completed.slack))
                end_entry = (dag_id_completed,dag_completed.priority,dag_completed.dag_type,dag_completed.slack, dag_completed.resp_time, dag_completed.noaffinity_time) #,dag_completed.energy)
                self.end_list.append(end_entry)
                # Remove DAG from active list
                self.dag_id_list.remove(dag_id_completed)
                del self.dag_dict[dag_id_completed]

    def push_ready_tasks(self):
        # Check for DAGs to be dropped
        if self.drop == True:
            temp_dropped_id_list = [] #Temporary list to remove dropped DAGs from main DAG ID list and DAG dict
            for dag_id in self.dag_id_list:
                the_dag_sched = self.dag_dict[dag_id]

                # if dag's arrival time is after current times do not process dropping for it
                if self.env.now < the_dag_sched.arrival_time:
                    break

                # If DAG ID in drop_hint_list from TSCHED, drop the DAG
                if self.drop_hint_list.contains(dag_id) and the_dag_sched.priority == 1:
                    # print("[ID: %d]Dropping based on hint from task scheduler" %(dag_id))
                    dropped_entry = (dag_id,the_dag_sched.priority,the_dag_sched.dag_type,the_dag_sched.slack, the_dag_sched.resp_time, the_dag_sched.noaffinity_time)
                    self.dropped_list.append(dropped_entry)
                    temp_dropped_id_list.append(dag_id)
                    continue

                for node,deg in the_dag_sched.graph.in_degree():
                    if deg == 0:
                        if node.scheduled == 0:
                            if(self.meta_policy.dropping_policy(the_dag_sched, node)):
                                # logging.info("%d: [DROPPED] DAG id: %d dropped" %(self.stomp.sim_time, dag_id))
                                dropped_entry = (dag_id,the_dag_sched.priority,the_dag_sched.dag_type,the_dag_sched.slack, the_dag_sched.resp_time, the_dag_sched.noaffinity_time)
                                self.dags_dropped.add(dag_id)
                                self.dropped_list.append(dropped_entry)
                                temp_dropped_id_list.append(dag_id)
                                break

            # Remove Dropped DAGs from active DAG list
            # Performing this at the end to not break the dag_id_list structure
            for dag_id_dropped in temp_dropped_id_list:
                self.dag_id_list.remove(dag_id_dropped)
                del self.dag_dict[dag_id_dropped]
            self.dags_dropped.add(temp_dropped_id_list)

        ## Check for ready tasks ##
        # self.print("dag_id_list: {}".format(self.dag_id_list))
        for dag_id in self.dag_id_list:
            the_dag_sched = self.dag_dict[dag_id]

            ## Push ready tasks into ready queue ##
            for task_node, deg in the_dag_sched.graph.in_degree():
                if deg == 0:
                    # PROMOTE DAGs
                    if(self.params['simulation']['promote'] == True):
                        if (the_dag_sched.arrival_time > \
                            (self.ticks_since_last_promote + self.promote_interval)) and \
                            the_dag_sched.priority == 1 and task_node.tid == 0:
                            # print("[%d]: [%d.%d.%d], atime: %d, time_threshold: %d, completed: %d\n" % (self.stomp.sim_time, dag_id, task_node.tid, the_dag_sched.priority, the_dag_sched.arrival_time, (self.ticks_since_last_promote + promote_interval), dags_completed_per_interval))
                            # print("[%d]: DAG id: %d, atime: %d, completed DAGs: %d\n" % (self.stomp.sim_time, dag_id, the_dag_sched.arrival_time, dags_completed_per_interval))
                            task_node.priority = 3
                            the_dag_sched.priority = 3
                            the_dag_sched.promoted = 1
                            # print("%d: [%d,%d]Dag promoted\n" %(self.stomp.sim_time, dag_id, task_node.tid))
                            self.ticks_since_last_promote = the_dag_sched.arrival_time

                    if task_node.scheduled == 0:
                        # PROMOTE DAGs
                        if(self.params['simulation']['promote'] == True):
                            # Revaluate promotion for non-zero tid
                            if (the_dag_sched.promoted == 1 and the_dag_sched.perm_promoted == 0 and task_node.tid != 0):
                                if self.dags_completed_per_interval > 0:
                                    task_node.priority = 1
                                    the_dag_sched.priority = 1
                                    the_dag_sched.promoted = 0
                                    # print("%d: [%d,%d]Dag demoted completed:%d\n" %(self.stomp.sim_time, dag_id, task_node.tid,dags_completed_per_interval))
                                else:
                                    # print("%d: [%d,%d]Dag remains promoted completed:%d\n" %(self.stomp.sim_time, dag_id, task_node.tid, dags_completed_per_interval))
                                    the_dag_sched.perm_promoted = 1
                                    self.last_promoted_dag_id = dag_id
                                self.dags_completed_per_interval = 0

                        # node 0 inherits arrival time from DAG's actual arrival
                        # time as in the trace file
                        if task_node.tid == 0:
                            atime = the_dag_sched.arrival_time
                        else:
                            atime = self.env.now
                        task_type = the_dag_sched.comp[task_node.tid][0]
                        priority = the_dag_sched.priority
                        deadline = int(the_dag_sched.slack)

                        #Use SDR for task deadline calculation
                        if (self.params['simulation']['policy'].startswith("ms1")):
                            deadline = int(the_dag_sched.deadline*float(the_dag_sched.comp[task_node.tid][1]))
                        elif (self.params['simulation']['policy'].startswith("ms2")):
                            deadline = int(deadline*float(the_dag_sched.comp[task_node.tid][1]))

                        # Initialize task during execution
                        task_node.init_task(atime, the_dag_sched.dag_type, dag_id, task_node.tid, task_type, self.params['simulation']['tasks'][task_type], priority, deadline, int(the_dag_sched.dtime))

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

                        task_node.max_time = max_time
                        task_node.min_time = min_time
                        # Dynamic Rank Assignment
                        start = datetime.now()
                        self.meta_policy.meta_dynamic_rank(self.stomp, task_node, the_dag_sched.comp, max_time, min_time, deadline, priority)
                        self.profiler.dranktime += datetime.now() - start

                        #### AFFINITY ####
                        # Pass parent id and HW id of parents with task
                        ####
                        parent_data = []
                        for parent in the_dag_sched.parent_dict[task_node.tid]:
                            parent_data.append((parent,the_dag_sched.completed_peid[parent]))
                        task_node.parent_data = parent_data

                        ## Ready task found, push into global ready task queue and create TASK ARRIVAL event
                        # self.print("global_task_trace = {}".format(self.global_task_trace))
                        ready_task = task_node
                        # self.print('Inserting @%u, DAG:%u, TID:%u' % (ready_task.arrival_time, ready_task.dag_id, ready_task.tid))
                        self.global_task_trace.put(ready_task.arrival_time, ready_task)
                        # self.print("self.global_task_trace = {}".format(self.global_task_trace))

                        # print("[meta] triggering stomp to start now")
                        self.tsched_eventq.put(ready_task.arrival_time, events.TASK_ARRIVAL)
                        # self.print("TSCHED event queue len is now: {}".format(self.tsched_eventq.qsize()))
                        self.stomp.action.interrupt()
                        task_node.scheduled = 1

        ## If all DAGs have completed update META is done
        if not self.dag_id_list:
            self.tsched_eventq.put(self.env.now, events.META_DONE)
            # self.print("Meta interrupting TSCHED")
            self.stomp.action.interrupt()
            self.meta_eventq.put(self.env.now, events.META_DONE)

    def populate_from_trace(self, in_trace_name, application):
        with open(in_trace_name, 'r') as input_trace:
            for line in input_trace.readlines():
                tmp = line.strip().split(',')
                atime = int(int(tmp.pop(0))*self.params['simulation']['arrival_time_scale'])
                dag_id = int(tmp.pop(0))
                dag_type = tmp.pop(0)

                graphml_file = "inputs/{0}/dag_input/dag{1}.graphml".format(application, dag_type)
                graph = nx.read_graphml(graphml_file, TASK)

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
                comp_file = "inputs/{0}/dag_input/dag_{1}.txt".format(application, dag_type)
                # if (self.params['simulation']['policy'].startswith("ms2")):
                #    comp_file = "inputs/{0}/dag_input/dag_{1}_slack.txt".format(application, dag_type)

                comp = read_matrix(comp_file)
                priority = int(tmp.pop(0))
                deadline = int(tmp.pop(0))*(self.params['simulation']['arrival_time_scale'])
                dtime = atime + deadline

                the_dag_trace = DAG(graph, comp, parent_dict, atime, deadline, dtime, priority, dag_type)
                the_dag_trace.dag_variables = self.meta_policy.set_dag_variables(the_dag_trace)
                self.dag_dict[dag_id] = the_dag_trace
                self.dag_id_list.append(dag_id)
                # if line_count == 0:
                #     self.meta_eventq.put(atime, events.DAG_ARRIVAL)

                ## Static ranking ##
                start = datetime.now()
                self.meta_policy.meta_static_rank(self.stomp, the_dag_trace)
                self.profiler.sranktime += datetime.now() - start
        
        self.pbar = tqdm(total=len(self.dag_id_list) if not self.drop else None)

    def run(self):
        self.meta_policy.init(self.params)
        # dummy event to keep the event queue running
        self.meta_eventq.put(self.max_timesteps, events.SIM_LIMIT)

        application = self.params['simulation']['application']
        ### Read input DAGs ####
        in_trace_name = self.working_dir + '/' + self.input_trace_file
        logging.info(in_trace_name)

        # wait for TSCHED to start
        self.env.all_of([self.stomp.action])

        ## Read trace file and populate DAG information ##
        ## This adds dags into dag_id_list in the order of their arrival time
        self.populate_from_trace(in_trace_name, application)

        start = datetime.now()
        self.push_ready_tasks()
        self.profiler.rtime += datetime.now() - start

        self.print("Running event loop")

        while True:
            tick, event = yield from handle_event(self.env, self.meta_eventq)
            message_decode_event(self, event)
            # self.print("tick: {}, event: {}".format(tick, event))

            if event == events.TASK_COMPLETED:
                start = datetime.now()
                self.handle_task_completion()
                self.profiler.ctime += datetime.now() - start
                start = datetime.now()
                self.push_ready_tasks()
                self.profiler.rtime += datetime.now() - start
            elif event == events.META_DONE:
                # self.print("Meta done!")
                break
            elif event == events.SIM_LIMIT:
                assert False
            else:
                raise NotImplementedError

        # Open output file and write DAG stats
        fho = open(self.params['general']['working_dir'] + '/run_stdout_' + self.params['general']['basename'] + '.out', 'w')
        fho.write("Dropped,DAG ID,DAG Priority,DAG Type,Slack,Response Time,No-Affinity Time\n")

        self.end_list.sort(key=lambda end_entry: end_entry[0], reverse=False)
        while self.end_list:
            end_entry = self.end_list.pop(0)
            fho.write("0," + str(end_entry[0]) + ',' + str(end_entry[1]) + ',' + str(end_entry[2]) + ',' + str(end_entry[3]) + ',' + str(end_entry[4]) + ',' + str(end_entry[5]) + '\n')

        if self.drop:
            self.dropped_list.sort(key=lambda dropped_entry: dropped_entry[0], reverse=False)
            while self.dropped_list:
                dropped_entry = self.dropped_list.pop(0)
                fho.write("1," + str(dropped_entry[0]) + ',' + str(dropped_entry[1]) + ',' + str(dropped_entry[2]) + ',' + str(dropped_entry[3]) + ',' + str(dropped_entry[4]) + ',' + str(dropped_entry[5]) + '\n')

        if self.all_tasks_energy == 0:
            logging.error("Energy could not be computed.")
            exit(1)

        #(Processing time for completed task, ready task time, static-rank time, dynamic rank time, task assignment, task ordering)
        fho.write(("Time: %d,%d,%d,%d,%d,%d\n")%(self.profiler.ctime.microseconds, self.profiler.rtime.microseconds, self.profiler.sranktime.microseconds, self.profiler.dranktime.microseconds, self.stomp.ta_time.microseconds, self.stomp.to_time.microseconds))
        if self.tasks_completed_count_crit == 0 and self.tasks_completed_count_nocrit != 0:
            fho.write(("nan, nan,%lf,%lf,%d,%u\n")%(self.wtr_nocrit/self.tasks_completed_count_nocrit, self.lt_wcet_r_nocrit/self.tasks_completed_count_nocrit, self.env.now, self.all_tasks_energy))
        elif self.tasks_completed_count_crit != 0 and self.tasks_completed_count_nocrit == 0:
            fho.write(("%lf,%lf, nan, nan,%d,%u\n")%(self.wtr_crit/self.tasks_completed_count_crit, self.lt_wcet_r_crit/self.tasks_completed_count_crit, self.env.now, self.all_tasks_energy))
        elif self.tasks_completed_count_crit == 0 and self.tasks_completed_count_nocrit == 0:
            fho.write(("nan, nan, nan, nan,%d,%u\n")%(self.env.now, self.all_tasks_energy))
        else:
            fho.write(("%lf,%lf,%lf,%lf,%d,%u\n")%(self.wtr_crit/self.tasks_completed_count_crit,
                self.lt_wcet_r_crit/self.tasks_completed_count_crit, self.wtr_nocrit/self.tasks_completed_count_nocrit,
                self.lt_wcet_r_nocrit/self.tasks_completed_count_nocrit, self.env.now, self.all_tasks_energy))

        fho.close()
