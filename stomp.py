#!/usr/bin/env python
#
# Copyright 2018 IBM
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
import operator
import logging
from datetime import timedelta
import datetime

import threading

from meta import TASK

###############################################################################
# This class represents a 'server' in the system; i.e. an entity that can     #
# process tasks. Each server has an associated 'type' (e.g. CPU, GPU, etc.)   #
# which determines how the assigned task is processed (speed, power, etc.)    #
###############################################################################
class Server:

    def __init__(self, id, type):

        self.id                 = id
        self.type               = type
        self.pmode              = None
        self.num_reqs           = 0
        self.last_stopped_at    = 0
        self.busy_time          = 0
        self.last_dag_id        = None
        self.last_task_id       = None

        self.stats                            = {}
        self.stats['Tasks Serviced']          = 0
        self.stats['Tasks Serviced per Type'] = {}
        self.stats['Avg Resp Time']           = 0     # Overall for all tasks
        self.stats['Avg Resp Time per Type']  = {}    # Per task type
        self.stats['Met Deadline']           = 0     # Overall for all tasks
        self.stats['Met Deadline per Type']  = {}    # Per task type
        self.stats['Service Time per Type']   = {}    # Per task type
        self.stats['Lifetime per Type']       = {}    # Per task type

        self.reset()

        logging.debug('Server %d of type %s created' % (self.id, self.type))


    def reset(self):

        self.busy                   = False
        self.curr_service_time      = None
        self.curr_job_start_time    = None
        self.curr_job_end_time      = None
        self.last_usage_started_at  = None
        self.task                   = None



    def assign_task(self, sim_time, task):

        # At this moment, we know the target server where the task will run.
        # Therefore, we can compute the task's service time
        task_dag_id                     = task.dag_id
        task_tid                        = task.tid
        task_priority                   = task.priority
        task_deadline                   = task.deadline
        mean_service_time               = task.mean_service_time_dict[self.type]
        stdev_service_time              = task.stdev_service_time_dict[self.type]
        service_time                    = task.per_server_service_dict[self.type] # Use the per-server type service time, indexed by server_type
        noaffinity_time                 = 0
        #service_time                     = int(round(numpy.random.normal(loc=mean_service_time, scale=stdev_service_time, size=1)))
        # Ensure that the random service time is a positive value...
        if (service_time <= 0):
            service_time                    = 1

        #### AFFINITY ####
        # Maintain dag_id + task id of last executed task
        # Calculate execution time based on if parent was last executed on the server
        ####
        # if self.last_dag_id != None:
        #     print("Server id: %d last DAG id and task id: %d,%d" % (self.id, self.last_dag_id, self.last_task_id))

        # print(task.parent_data)
        for parent in task.parent_data:
            if parent[1]  == self.id and parent[0] == self.last_task_id and task_dag_id == self.last_dag_id:
                noaffinity_time             += 0
            else:
                noaffinity_time             += 0.25 * task.mean_service_time_dict[self.type]
                # print("No Affinity for parent %lf" % (noaffinity_time))
        task.noaffinity_time = int(noaffinity_time)
        task.server_type = self.type


        task.task_service_time              = service_time + task.noaffinity_time
        self.busy                           = True
        self.curr_service_time              = task.task_service_time
        self.curr_job_start_time            = sim_time
        self.curr_job_end_time              = self.curr_job_start_time + self.curr_service_time
        self.curr_job_end_time_estimated    = self.curr_job_start_time + mean_service_time + task.noaffinity_time
        self.last_usage_started_at          = sim_time
        self.num_reqs                       += 1
        self.task                           = task

        self.busy_time                      += self.curr_service_time
        self.last_dag_id                    = task_dag_id
        self.last_task_id                   = task_tid

        logging.debug("[%10ld] Assigned task %d %s : srv %d st %d end %d est %d" % (sim_time, task.trace_id, task.type, self.curr_service_time, self.curr_job_start_time, self.curr_job_end_time, self.curr_job_end_time_estimated))



    def __str__(self):
        return ('Server ' + str(self.id) + ' (' + self.type + ')\n'
                '  Busy:         ' + str(self.busy) + '\n'
                '  Task:         ' + self.task.type + '\n'
                '  Service Time: ' + str(self.curr_service_time) + '\n'
                )


class BaseSchedulingPolicy:

    __metaclass__ = ABCMeta

    @abstractmethod
    def init(self, servers, stomp_stats, stomp_params): pass

    @abstractmethod
    def assign_task_to_server(self, sim_time, tasks, dags_dropped): pass

    @abstractmethod
    def remove_task_from_server(self, sim_time, server): pass

    @abstractmethod
    def output_final_stats(self, sim_time): pass


###############################################################################
# >>>>>>> THIS IS THE MAIN CLASS THAT IMPLEMENTS THE QUEUE SIMULATOR <<<<<<<< #
#                                                                             #
# This class takes care of:                                                   #
#   - Generation and enqueing of new tasks.                                   #
#   - Assignment of tasks to (available) servers.                             #
#   - Release of servers upon task completion.                                #
#   - Other simulation-related aspects.                                       #
# The entire simulation is performed by calling the run() function.           #
###############################################################################
class STOMP:

    # Events: event-driven simulation
    E_PWR_MGMT          = 1
    E_TASK_ARRIVAL      = 2
    E_SERVER_FINISHES   = 3
    E_NOTHING           = 4

    E_META_START        = 0
    E_META_DONE         = 0

    E_TSCHED_DONE       = 0


    def __init__(self, stomp_params, sched_policy):

        self.params       = stomp_params
        self.sched_policy = sched_policy
        self.working_dir  = self.params['general']['working_dir']
        self.basename     = self.params['general']['basename']
        self.num_tasks_generated = 0
        self.time_since_last_completed = 0

        logging.basicConfig(level=eval('logging.' + self.params['general']['logging_level']), format="%(message)s")

        numpy.random.seed(self.params['general']['random_seed'])

        #pprint.pprint(self.params)
        logging.info("CONFIGURATION:\n%s\n" % (self.params))  #pprint.pprint(self.params))

        self.tasks                            = []   # Main queue
        self.servers                          = []
        self.tasks_to_servers                 = {}   # Maps task type to target servers
        #self.supported_servers               = []

        self.intrace_server_order             = []

        self.sim_time                         = 0    # Simulation time
        self.ta_time                          = timedelta(microseconds = 0)
        self.to_time                          = timedelta(microseconds = 0)

        # Global stats
        self.stats                            = {}
        self.stats['Running Tasks']           = 0
        self.stats['Busy Servers']            = 0
        self.stats['Available Servers']       = {}
        self.stats['Tasks Generated']         = 0
        self.stats['Tasks Generated by META']         = 0
        self.stats['Tasks Serviced']          = 0
        self.stats['Tasks Serviced per Type'] = {}
        self.stats['Avg Resp Time']           = 0     # Overall for all tasks
        self.stats['Avg Resp Time per Type']  = {}    # Per task type
        self.stats['Met Deadline']            = 0     # Overall for all tasks
        self.stats['Met Deadline per Type']   = {}    # Per task type

        # Histograms
        self.bin_size                         = 1
        self.num_bins                         = 12
        self.last_size_change_time            = self.sim_time
        self.stats['Queue Size Histogram']    = numpy.zeros(self.num_bins, dtype=int)  # N-bin histogram
        self.stats['Max Queue Size']          = 0

        self.task_trace_files                 = {}   # Per task type
        self.task_trace_file                  = open(self.working_dir + '/' + self.basename + '.global.trace', 'w')
        # self.task_trace_file.write('%s\n\n' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        # self.task_trace_file.write("CONFIGURATION:\n%s\n" % (self.params))  #pprint.pprint(self.params))
        self.task_trace_file.write(
            'sim_time,'
            'avg_resp_time,'
            'task_trace_id,'
            'task_type,'
            'id,'
            'type,'
            'curr_service_time,'
            'task_dag_id,'
            'task_tid,'
            'task_priority,'
            'dag_dtime,'
            'task_parent_ids,'
            'task_arrival_time,'
            'curr_job_start_time,'
            'curr_job_end_time\n'
        )

        self.task_assign_trace                = open(self.working_dir + '/' + self.basename + '.global.atrace', 'w')
        self.task_assign_trace.write('%s\n\n' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.task_assign_trace.write("CONFIGURATION:\n%s\n" % (self.params))  #pprint.pprint(self.params))
        self.task_assign_trace.write('Time\tResponse time (avg)\n')

        self.dags_dropped                     = []
        self.tasks_completed                  = []
        self.next_event                       = STOMP.E_NOTHING
        self.next_task_event                  = STOMP.E_NOTHING
        self.next_server_event                = STOMP.E_NOTHING


        self.init_servers()

        # IF user specified an input trace file then read that in here:
        self.global_task_trace = []
        self.lock = threading.Lock()        #For safe access of global_task_trace
        self.tlock = threading.Lock()       #For safe access of tasks_completed and task_completed_flag
        self.task_completed_flag = 0
        self. random = 0
        if (stomp_params['general']['input_trace_file']):
            self.arrival_trace    = stomp_params['general']['input_trace_file'][0]
            self.input_trace_file = None #stomp_params['general']['input_trace_file'][1]
        else:
            self.arrival_trace    = None
            self.input_trace_file = None

        self.output_trace_file = stomp_params['general']['output_trace_file']

        self.pre_gen_arrivals = stomp_params['general']['pre_gen_arrivals']

        if (self.input_trace_file and self.pre_gen_arrivals):
            logging.info('WARNING: both an input task arrival trace file and pre-gen arrivals options specified; using the input trace\n')


        if (self.output_trace_file):
            out_trace_name = self.working_dir + '/' + self.output_trace_file
            logging.info('Generating output trace file to %s' % (out_trace_name))
            self.output_trace = open(out_trace_name, 'w')
            self.output_trace.write('%s\n' % ','.join(map(str, self.params['simulation']['servers'])))




    def init_servers(self):

        id = 0
        for server_type in self.params['simulation']['servers']:
            if not server_type in self.stats['Available Servers']:
                self.stats['Available Servers'][server_type] = self.params['simulation']['servers'][server_type]['count']
            server_count = self.params['simulation']['servers'][server_type]['count']
            for i in range(server_count):
                self.servers.append(Server(id, server_type))
                id += 1

            #self.supported_servers.append(server_type)


    def generate_n_enqueue_new_task(self, task_num):

        if (len(self.tasks) == self.params['simulation']['max_queue_size']):
            logging.info('[%10ld] Problem with finding an empty queue slot!' % (self.sim_time))
            return False

        # Update histogram
        queue_size  = len(self.tasks)
        bin         = int(queue_size / self.bin_size)
        time_period = self.sim_time - self.last_size_change_time
        if (self.stats['Max Queue Size'] < queue_size):
            self.stats['Max Queue Size'] = queue_size
        if (bin >= len(self.stats['Queue Size Histogram'])):
            bin = len(self.stats['Queue Size Histogram']) - 1
        self.stats['Queue Size Histogram'][bin] += time_period
        self.last_size_change_time = self.sim_time

        #if (self.stats['Queue Size Histogram'][6] > 0):
        #    logging.info('1> At time %ld have Q_size[%d] = %d' % (self.sim_time, 6, self.stats['Queue Size Histogram'][6]))
        #    logging.info(' qSize %d  bin  %d  time_period %d' % (queue_size, bin, time_period))

        # Create and enqueue a new task
        # Select the "type" of task to create
        # NOTE: self.global_task_trace is used for EITHER an input trace or pre-gen arrival trace behavior
        tr_entry = []
        # logging.info("Start")
        if (self.global_task_trace):
            self.lock.acquire()
            if (len(self.global_task_trace) > 0):
                tr_entry = self.global_task_trace.pop(0)
            self.lock.release()
            # logging.info('ARR_TR : %s' % tr_entry)

            # #logging.info('   PSD : %s' % the_task.per_server_service_dict)

            the_task = tr_entry
            the_task.trace_id = task_num
            task = the_task.type

            # logging.debug('[%10ld] Setting next task type from TRACE to %s' % (self.sim_time, task))


            # print("Task:")
            # print(the_task.dag_id,
            #     the_task.tid,
            #     the_task.priority,
            #     the_task.deadline,
            #     the_task.dtime,
            #     the_task.rank,
            #     the_task.est,
            #     the_task.eft,
            #     the_task.subD,
            #     the_task.lst,
            #     the_task.ftsched)
            # print(the_task.per_server_services)

            # for serv in self.servers:
            #     print(serv.type,the_task.per_server_service_dict[serv.type])

            # logging.info("Task rank: %d,%d,%d,%d,%d" % (the_task.rank, the_task.priority, the_task.deadline, sum_time, num_servers))
            self.tasks.append(the_task)
            self.stats['Tasks Generated'] += 1

            if (self.output_trace_file):
                self.output_trace.write('%d,%s,%d,%d,%d,%d,%d,%s\n' % (self.sim_time, task, the_task.dag_id, the_task.tid, the_task.size, the_task.priority, the_task.deadline, ','.join(map(str, the_task.per_server_services))))


            if not task in self.stats['Avg Resp Time per Type']:
                self.stats['Avg Resp Time per Type'][task]  = 0
                self.stats['Met Deadline per Type'][task]   = 0
                self.stats['Tasks Serviced per Type'][task] = 0
                self.task_trace_files[task] = open(self.working_dir + '/' + self.basename + '.' + task + '.' + self.params['simulation']['sched_policy_module'].split('.')[-1] + '.trace', 'w')

                self.task_trace_files[task].write('%s\n\n' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                self.task_trace_files[task].write("CONFIGURATION:\n%s\n" % (self.params))  #pprint.pprint(self.params))
                self.task_trace_files[task].write('Time\tResponse time (avg)\n')

        return True



    def release_server(self, server):

        # Update statistics
        task_type = server.task.type

        resp_time = (self.sim_time - server.task.arrival_time)
        server.task.task_lifetime = resp_time
        server.task.peid = server.id
        self.tlock.acquire()
        self.tasks_completed.append(server.task)
        self.task_completed_flag = 1
        # print('Task completed : %d,%d,%d' % (self.sim_time,server.task.dag_id,server.task.tid)) #Aporva
        # self.next_cust_arrival_time = int(round(self.sim_time))
        self.time_since_last_completed = 0

        self.tlock.release()


        if not task_type in server.stats['Avg Resp Time per Type']:
            server.stats['Avg Resp Time per Type'][task_type]  = 0
            server.stats['Tasks Serviced per Type'][task_type] = 0
            server.stats['Service Time per Type'][task_type]   = []
            server.stats['Lifetime per Type'][task_type]       = []

        server.stats['Avg Resp Time']                      += resp_time
        server.stats['Avg Resp Time per Type'][task_type]  += resp_time
        server.stats['Tasks Serviced']                     += 1
        server.stats['Tasks Serviced per Type'][task_type] += 1
        server.stats['Service Time per Type'][task_type].append(server.task.task_service_time)
        server.stats['Lifetime per Type'][task_type].append(server.task.task_lifetime)
        self.stats['Avg Resp Time']                     += resp_time
        self.stats['Avg Resp Time per Type'][task_type] += resp_time
        if (resp_time <= server.task.deadline):
            self.stats['Met Deadline']                      += 1
            self.stats['Met Deadline per Type'][task_type]  += 1
        #avg_serv_time       = (avg_serv_time * (num_tasks_serviced - 1) + server_entry['task']['task_service_time']) / num_tasks_serviced
        #int_resp_time  = (int_resp_time*(int_num_tasks_serviced-1) +
        #                 (SIM_TIME-server[SERVER_ID].cust.arrival_time)) / int_num_tasks_serviced
        #int_serv_time = (int_serv_time*(int_num_tasks_serviced-1)+server[SERVER_ID].cust.task_service_time)/int_num_tasks_serviced


        self.stats['Tasks Serviced']                     += 1
        self.stats['Tasks Serviced per Type'][task_type] += 1
        self.stats['Busy Servers']                       -= 1
        self.stats['Available Servers'][server.type]     += 1
        self.next_serv_end_time                           = float("inf")
        self.next_serv_end                                = None

        avg_resp_time = self.stats['Avg Resp Time'] / self.stats['Tasks Serviced']
        self.task_trace_file.write('%ld,%.1f,%d,%s,%d,%s,%d,%d,%d,%d,%d,%s,%d,%d,%d\n' % (
            self.sim_time,
            avg_resp_time,
            server.task.trace_id,
            server.task.type,
            server.id,
            server.type,
            server.curr_service_time,
            server.task.dag_id,
            server.task.tid,
            server.task.priority,
            server.task.dtime,
            str([x for (x,y) in server.task.parent_data]).replace(',', '')[1:-1],
            server.task.arrival_time,
            server.curr_job_start_time,
            server.curr_job_end_time)
        )

        avg_resp_time = self.stats['Avg Resp Time per Type'][task_type] / self.stats['Tasks Serviced per Type'][task_type]
        self.task_trace_files[task_type].write('%ld\t%.1f\n' % (self.sim_time, avg_resp_time))

        self.sched_policy.remove_task_from_server(self.sim_time, server)

        server.reset()
        server.last_stopped_at = self.sim_time

        # Determine next server end time
        for server in self.servers:
            if (server.busy and server.curr_job_end_time <= self.next_serv_end_time):
                self.next_serv_end_time  = server.curr_job_end_time
                self.next_serv_end       = server


    def print_stats(self):

        self.stats['Avg Resp Time'] = self.stats['Avg Resp Time'] / self.stats['Tasks Serviced']

        # Final histogram update
        queue_size  = len(self.tasks)
        bin         = int(queue_size / self.bin_size)
        time_period = self.sim_time - self.last_size_change_time
        if (bin >= len(self.stats['Queue Size Histogram'])):
            bin = len(self.stats['Queue Size Histogram']) - 1
        self.stats['Queue Size Histogram'][bin] += time_period
        self.last_size_change_time = self.sim_time

        # Normalize histogram
        total_time = numpy.sum(self.stats['Queue Size Histogram'])
        pct_qsize = numpy.around(100 * self.stats['Queue Size Histogram'] / total_time, decimals=2)


        ##### DUMP STATISTICS TO STDOUT #####

        logging.info('\n==================== Simulation Statistics ====================')
        logging.info(' Total simulation time: %ld' % self.sim_time)
        logging.info(' Tasks serviced:        %ld' % self.stats['Tasks Serviced'])
        logging.info('')

        logging.info(' Met Deadline:')
        logging.info('   %12s : %8d over %8d tasks' % ("global", self.stats['Met Deadline'], self.stats['Tasks Serviced']))
        for task in self.stats['Met Deadline per Type']:
            if (self.stats['Tasks Serviced per Type'][task] > 0):
                logging.info('   %12s : %8d over %8d tasks' % (task, self.stats['Met Deadline per Type'][task], self.stats['Tasks Serviced per Type'][task]))
            else:
                logging.info('   %12s : %8,2f over %8d tasks' % (task, 0.0, 0))
        logging.info('')

        logging.info(' Response time (avg):')
        logging.info('   %12s : %8.2f over %8d tasks' % ("global", self.stats['Avg Resp Time'], self.stats['Tasks Serviced']))
        for task in self.stats['Avg Resp Time per Type']:
            if (self.stats['Tasks Serviced per Type'][task] > 0):
                logging.info('   %12s : %8.2f over %8d tasks' % (task, self.stats['Avg Resp Time per Type'][task]/self.stats['Tasks Serviced per Type'][task], self.stats['Tasks Serviced per Type'][task]))
            else:
                logging.info('   %12s : %8,2f over %8d tasks' % (task, 0.0, 0))
        logging.info('')

        logging.info(' Server Response time (avg):')
        for server in self.servers:
            if (server.stats['Tasks Serviced'] > 0):
                server.stats['Avg Resp Time'] = server.stats['Avg Resp Time'] / server.stats['Tasks Serviced']
                logging.info('   Server %3d : %12s : %8.2f over %8d tasks' % (server.id, "global", server.stats['Avg Resp Time'], server.stats['Tasks Serviced']))
            else:
                logging.info('   Server %3d : %12s : %8.2f over %8d tasks' % (server.id, "global", 0.0, 0))

        logging.info('')
        for server in self.servers:
            for task in server.stats['Avg Resp Time per Type']:
                if (server.stats['Tasks Serviced per Type'][task] > 0):
                    logging.info('   Server %3d : %12s : %8.2f over %8d tasks' % (server.id, task, server.stats['Avg Resp Time per Type'][task]/server.stats['Tasks Serviced per Type'][task], server.stats['Tasks Serviced per Type'][task]))
                else:
                    logging.info('   Server %3d : %12s : %8.2f over %8d tasks' % (server.id, task, 0.0, 0))
        logging.info('')

        logging.info(' Busy time and Utilization:')
        logging.info('                %12s  : %10s  %5s' % ("Server Type", "Busy Time", "Util."))
        for server in self.servers:
            logging.info('   Server %3d ( %12s ): %10ld  %5.2f' % (server.id, server.type, server.busy_time, numpy.around(100 * server.busy_time / total_time, decimals=2)))
        logging.info('')

        #logging.info(' Utilization:')
        #for server in self.servers:
        #    logging.info('   Server %3d ( %12s ): %.1f' % (server.id, server.type, 100*server.busy_time/self.sim_time))
        #logging.info('')

        logging.info(' Histograms:')
        #logging.info('   Queue size Pct time (bin size=%d): %s' % (self.bin_size, ', '.join(map(str,self.stats['Queue Size Histogram']))))
        logging.info('   Queue size Pct time: bin_size, %d , max_In_Queue, %d , %s' % (self.bin_size, self.stats['Max Queue Size'],', '.join(map(str,self.stats['Queue Size Histogram']))))
        idx = 0;
        bin = 0;
        logging.info('         %4s  %10s  %8s  %10s  %8s' % ("Bin", "Tot Time", "Pct Time", "Cum Time", "Cum Pct"))
        c_time = 0
        c_pct_time = 0
        for count in self.stats['Queue Size Histogram']:
            sz = numpy.around(100 * count / total_time, decimals=2)
            c_time += count
            c_pct_time += sz
            sbin = str(bin)
            logging.info('         %4s  %10d    %6.2f  %10d    %6.2f' % (sbin, count, sz, c_time, c_pct_time))
            idx += 1
            if (idx < (self.num_bins - 1)):
                bin += self.bin_size
            else:
                bin = ">" + str(bin)
        logging.info('')

        server = self.sched_policy.output_final_stats(self.sim_time)

        logging.info(' Per Server Task Service Times Analysis:')
        for server in self.servers:
            for task in server.stats['Avg Resp Time per Type']:
                anum = float(0.0)
                for rt in server.stats['Service Time per Type'][task]: #.append(resp_time)
                    anum += rt
                #avg = numpy.around(100 * anum / len(server.stats['Service Time per Type'][task]), decimals=2)
                avg = anum / len(server.stats['Service Time per Type'][task])
                num = float(0.0)
                for rt in server.stats['Service Time per Type'][task]: #.append(resp_time)
                    num += (rt - avg)*(rt - avg)
                    #logging.info('STDEV_CMP,Server,%d,task,%s,%d,%d' % (server.id, task, avg, rt))
                stdv = numpy.sqrt(num / len(server.stats['Service Time per Type'][task]))
                #logging.info('   Server %3d : %12s : Avg %8.2f vs %8.2f : StDev %8.2f vs %8.2f : over %8d tasks' % (server.id, task,
                # logging.info('   Server %3d : %12s : Avg %8.2f vs %8.3f : StDev %8.2f vs %8.3f : over %8d tasks' % (server.id, task,
                #                                                                                                     avg,  2*self.params['simulation']['tasks'][task]['server_factor'][server.type]*task.size,
                #                                                                                                     #stdv, (self.params['simulation']['tasks'][task]['stdev_service_time'][server.type] * self.params['simulation']['tasks'][task]['mean_service_time'][server.type]),
                #                                                                                                     stdv, self.params['simulation']['tasks'][task]['server_stdev_factor'][server.type]*self.params['simulation']['tasks'][task]['server_factor'][server.type]*task.size,
                #                                                                                                     len(server.stats['Service Time per Type'][task])))
        logging.info('')
        logging.info(' Server Type Task Type Service Times Analysis:')
        for server_type in self.params['simulation']['servers']:
            for task_type in self.params['simulation']['tasks']:
                anum = float(0.0)
                aden = 0
                avg = 0
                stdev = 0
                for server in self.servers:
                    if (server.type == server_type):
                        if (task_type in server.stats['Service Time per Type'].keys()):
                            for rt in server.stats['Service Time per Type'][task_type]:
                                anum += rt
                                aden += 1
                if (aden > 0):
                    avg = anum / float(aden)
                    snum = float(0.0)
                    sden = 0
                    for server in self.servers:
                        if (server.type == server_type):
                            if (task_type in server.stats['Service Time per Type'].keys()):
                                for rt in server.stats['Service Time per Type'][task_type]:
                                    snum += (rt - avg)*(rt - avg)
                                    sden += 1
                    stdv = numpy.sqrt(snum / float(sden))
                    # logging.info('   %12s : %12s : Avg %8.2f vs %8.3f : StDev %8.2f vs %8.3f : over %8d tasks' % (server_type, task_type,
                    #                                                                                               avg,  2*self.params['simulation']['tasks'][task]['server_factor'][server.type]*task.size,
                    #                                                                                               stdv, self.params['simulation']['tasks'][task]['server_stdev_factor'][server.type]*self.params['simulation']['tasks'][task]['server_factor'][server.type]*task.size,
                    #                                                                                               sden))


            #logging.info('')

        logging.info('')
        logging.info(' Per Server Task Wait Times (in-Queue) Analysis:')
        for server in self.servers:
            #for task_type in self.params['simulation']['tasks']:
            for task in server.stats['Avg Resp Time per Type']:
                anum = float(0.0)
                aden = 0
                for st,lt in zip(server.stats['Service Time per Type'][task], server.stats['Lifetime per Type'][task]):
                    wt = lt - st
                    anum += wt
                    #logging.info('%s %s %d %d %d' % (server.type, task, lt, st, wt))
                avg = anum / len(server.stats['Service Time per Type'][task])
                num = float(0.0)
                for st,lt in zip(server.stats['Service Time per Type'][task], server.stats['Lifetime per Type'][task]):
                    wt = float(lt - st)
                    num += (wt - avg)*(wt - avg)
                stdv = numpy.sqrt(num / len(server.stats['Service Time per Type'][task]))
                logging.info('   Server %3d %12s : %12s : Avg %8.2f : StDev %8.2f : over %8d tasks' % (server.id, server.type, task, avg, stdv, len(server.stats['Service Time per Type'][task])))

        logging.info('')
        logging.info(' Server Type Task Type Wait Times (in-Queue) Analysis:')
        for server_type in self.params['simulation']['servers']:
            for task_type in self.params['simulation']['tasks']:
                anum = float(0.0)
                aden = 0
                avg = 0
                stdev = 0
                for server in self.servers:
                    if (server.type == server_type):
                        if (task_type in server.stats['Service Time per Type'].keys()):
                            for st,lt in zip(server.stats['Service Time per Type'][task_type], server.stats['Lifetime per Type'][task_type]):
                                wt = lt - st
                                anum += wt
                                aden += 1
                if (aden > 0):
                    avg = anum / float(aden)
                    snum = float(0.0)
                    sden = 0
                    for server in self.servers:
                        if (server.type == server_type):
                            if (task_type in server.stats['Service Time per Type'].keys()):
                                for st,lt in zip(server.stats['Service Time per Type'][task_type], server.stats['Lifetime per Type'][task_type]):
                                    wt = float(lt - st)
                                    snum += (wt - avg)*(wt - avg)
                                    sden += 1
                    stdv = numpy.sqrt(snum / float(sden))
                    logging.info('   %12s : %12s : Avg %8.2f : StDev %8.2f : over %8d tasks' % (server_type, task_type, avg, stdv, sden))

        logging.info('')
        logging.info('')



    def run(self):

        logging.info('\nRunning STOMP simulation...')

        # This is because some scheduling policies may need to know about
        # the existent servers in order to make scheduling decisions
        self.sched_policy.init(self.servers, self.stats, self.params)

        # Force a task to arrive now
        self.next_cust_arrival_time  = self.sim_time
        self.next_power_mgmt_time    = float("inf")
        self.next_serv_end_time      = float("inf")
        self.next_serv_end           = None

        ######################################################################
        # MAIN SIMULATION: Generate 'max_tasks_simulated' and service them   #
        ######################################################################
        i = 0
        while(self.E_META_START == 0):
            pass
            # logging.info("Waiting for tasks to be generated")
        count = 0
        while ((len(self.tasks) > 0) or              # There are tasks in the queue, waiting to be served
              (self.stats['Busy Servers'] > 0) or   # There are tasks being served in the servers
              (self.E_META_DONE == 0)):             # Meta scheduler has pushed all ready tasks

            # Main duty loop: handle whichever simulation event occurs
            # earliest, then revert here in next iteration of main loop

            ######################################################################
            # 1) Determine next event to handle                                  #
            ######################################################################

            if (self.params['simulation']['power_mgmt_enabled'] and
               ((self.next_power_mgmt_time <= self.next_cust_arrival_time) or (self.stats['Tasks Generated'] >= self.params['simulation']['max_tasks_simulated'])) and
               (self.next_power_mgmt_time <= self.next_serv_end_time)):

                # Next event is a power management event
                self.next_event = STOMP.E_PWR_MGMT

            else:
                if ((self.stats['Tasks Generated by META']) and
                     (self.next_cust_arrival_time == self.sim_time)):
                    # Next event is a task arrival
                    self.next_task_event = STOMP.E_TASK_ARRIVAL


                if ((self.next_serv_end_time == self.sim_time)):

                    # Next event is a server finishing the execution of its assigned task
                    self.next_server_event = STOMP.E_SERVER_FINISHES

            # if((self.next_task_event != STOMP.E_NOTHING) or (self.next_server_event != STOMP.E_NOTHING)):
            #     print(str(self.sim_time) + " Event: " +
            #         "T: " + str((self.next_task_event != STOMP.E_NOTHING)) +
            #         " S: " + str((self.next_server_event != STOMP.E_NOTHING)) +
            #         " CAT: " + str(self.next_cust_arrival_time) +
            #         " NSET: " + str(self.next_serv_end_time) + " GT: " + str(len(self.global_task_trace)))               #Aporva
            ######################################################################
            # 2) Handle the event                                                #
            ######################################################################
            if (self.next_event == STOMP.E_PWR_MGMT):
                if (self.next_power_mgmt_time < self.sim_time):
                    logging.info('WARNING: PWR_MGMT Time Moving Backward: sim_time %ld but smaller next_power_mgmt_time %ld' % (self.sim_time, self.next_power_mgmt_time))
                # Manage power...
                self.sim_time = self.next_power_mgmt_time
                logging.info("A: " + str(self.sim_time))
                logging.warning('[%10ld] Power management not yet supported...' % (self.sim_time))

            if (self.next_task_event == STOMP.E_TASK_ARRIVAL):
                if (self.next_cust_arrival_time < self.sim_time):
                    logging.info('WARNING: TASK_ARRIVAL Time Moving Backward: sim_time %ld but smaller next_cust_arrival_time %ld' % (self.sim_time, self.next_cust_arrival_time))




                # logging.info(self.sim_time, len(self.global_task_trace))

                # Customer (task) arrival...
                if (len(self.global_task_trace)):

                    self.lock.acquire()
                    tmp = self.global_task_trace[0]
                    self.lock.release()
                    if (self.sim_time == int(tmp.arrival_time)):
                        # Customer (task) arrival...
                        # self.sim_time = self.next_cust_arrival_time
                        # logging.info("B: " + str(self.sim_time))
                        # Add task to queue
                        if (self.generate_n_enqueue_new_task(self.num_tasks_generated)):
                            self.num_tasks_generated += 1
                    else:
                        if(self.next_cust_arrival_time > int(tmp.arrival_time)):
                            # self.sim_time = int(tmp.arrival_time) - 1
                            self.next_cust_arrival_time = int(tmp.arrival_time) - 1
                            # print("SB: " + str(self.next_cust_arrival_time))
                            # logging.info("C: " + str(self.sim_time))
                    # self.next_cust_arrival_time = int(tmp.arrival_time)
                    logging.debug('[%10ld] Setting next task arrival time from TRACE to %d ( %s )' % (self.sim_time, self.next_cust_arrival_time, tmp.arrival_time))

                    if (len(self.global_task_trace)):
                            self.next_cust_arrival_time = int(self.global_task_trace[0].arrival_time)
                            # print("SC: " + str(self.next_cust_arrival_time))


                    # if (self.next_cust_arrival_time < self.sim_time):
                    #     logging.info('Random WARNING: TASK_ARRIVAL Time Moving Backward: sim_time %ld but smaller next_cust_arrival_time %ld' % (self.sim_time, self.next_cust_arrival_time))
                else:
                # if (self.task_completed_flag != 1):
                    self.next_cust_arrival_time = int(round(self.next_cust_arrival_time + 1))
                    # print("SD: " + str(self.next_cust_arrival_time))
                        # self.next_cust_arrival_time = None
                logging.debug('[%10ld] Task enqueued. Next task will arrive at time %ld' % (self.sim_time, self.next_cust_arrival_time))
                logging.debug('               Running tasks: %d, busy servers: %d, waiting tasks: %d' % (self.stats['Running Tasks'], self.stats['Busy Servers'], len(self.tasks)))


            if (self.next_server_event == STOMP.E_SERVER_FINISHES):
                # logging.info("NSE:" + str(self.next_serv_end))
                if (self.next_serv_end_time < self.sim_time):
                    logging.info('WARNING: SERVER_FINISH Time Moving Backward: sim_time %ld but smaller next_serv_end_time %ld' % (self.sim_time, self.next_serv_end_time))


                # Service completion (next_cust_arrival_time >= next_serv_end_time)
                # self.sim_time = self.next_serv_end_time
                # logging.info("D: " + str(self.sim_time))

                assert(not self.next_serv_end is None);
                self.release_server(self.next_serv_end)
                self.stats['Running Tasks'] -= 1

                logging.debug('[%10ld] Server finished' % (self.sim_time))
                logging.debug('             Running tasks: %d, busy servers: %d, waiting tasks: %d' % (self.stats['Running Tasks'], self.stats['Busy Servers'], len(self.tasks)))


            ######################################################################
            # 3) Make scheduling decisions                                       #
            ######################################################################
            server = self.sched_policy.assign_task_to_server(self.sim_time, self.tasks, self.dags_dropped)
            self.ta_time = self.sched_policy.ta_time
            self.to_time = self.sched_policy.to_time

            #print(server)
            if server is not None:
                if server.curr_job_end_time < self.next_serv_end_time:
                    self.next_serv_end_time = server.curr_job_end_time
                    self.next_serv_end      = server

                self.stats['Running Tasks']                  += 1
                self.stats['Busy Servers']                   += 1
                self.stats['Available Servers'][server.type] -= 1

                self.task_assign_trace.write('%ld,%d,%s,%d,%s,%d,%d,%d\n' % (self.sim_time, server.task.trace_id, server.task.type, server.id, server.type, server.curr_job_start_time, server.curr_service_time, server.curr_job_end_time))

                # Update histogram
                queue_size  = len(self.tasks) + 1  # +1 because the task was already removed
                if (self.stats['Max Queue Size'] < queue_size):
                    self.stats['Max Queue Size'] = queue_size
                bin         = int(queue_size / self.bin_size)
                time_period = self.sim_time - self.last_size_change_time
                if (bin >= len(self.stats['Queue Size Histogram'])):
                    bin = len(self.stats['Queue Size Histogram']) - 1
                self.stats['Queue Size Histogram'][bin] += time_period
                self.last_size_change_time = self.sim_time

                logging.debug('[%10ld] Task %d scheduled in server %d ( %s ) until %d' % (self.sim_time, server.task.trace_id, server.id, server.type, server.curr_job_end_time))
                logging.debug('               Running tasks: %d, busy servers: %d, waiting tasks: %d' % (self.stats['Running Tasks'], self.stats['Busy Servers'], len(self.tasks)))
                logging.debug('               Avail: %s' % (', '.join(['%s: %s' % (key, value) for (key, value) in self.stats['Available Servers'].items()])))

            # ######################################################################
            # # 4) Update sim time                                       #
            # ######################################################################
            # print("%d CAT: %lf, NSET: %lf" % (count,self.next_cust_arrival_time,self.next_serv_end_time)) #Aporva
            while(self.task_completed_flag == 1):
                pass
            if self.next_cust_arrival_time > self.sim_time and \
                self.next_serv_end_time > self.sim_time:

                self.sim_time += 1
                self.time_since_last_completed += 1
                if self.time_since_last_completed > self.params['simulation']['progress_intvl_f'] * \
                    self.params['simulation']['mean_arrival_time'] * \
                    self.params['simulation']['arrival_time_scale']:
                    logging.warning('[%10ld] WARNING: No completed activity since last %u timesteps' %
                        (self.sim_time, self.time_since_last_completed))

                # print("Time:" + str(self.sim_time)) #Aporva
            self.next_event = STOMP.E_NOTHING
            self.next_task_event = STOMP.E_NOTHING
            self.next_server_event = STOMP.E_NOTHING
            count += 1

            # print(("TSCHED Stats: Ready Tasks: %d, Busy Servers: %d, E_META_DONE: %d") % (len(self.tasks), self.stats['Busy Servers'], self.E_META_DONE))


        self.E_TSCHED_DONE = 1

        # Close task trace files
        self.task_trace_file.close()
        self.task_assign_trace.close()

        for task in self.task_trace_files:
            self.task_trace_files[task].close()

        if (self.output_trace_file):
            self.output_trace.close()

        # print("STOMP Completed")
