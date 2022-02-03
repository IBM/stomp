#!/usr/bin/env python3
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

from __future__ import division, print_function
from abc import ABCMeta, abstractmethod
import numpy
import pprint
import sys
import simpy
import operator
import logging
from datetime import timedelta
import datetime
import threading
from utils import MyPriorityQueue, EventQueue, message_decode_event, events, bcolors, handle_event

from meta import TASK

###############################################################################
# This class represents a 'server' in the system; i.e. an entity that can     #
# process tasks. Each server has an associated 'type' (e.g. CPU, GPU, etc.)   #
# which determines how the assigned task is processed (speed, power, etc.)    #
###############################################################################
class Server:

    def __init__(self, id, type, stomp_obj):

        self.id                 = id
        self.type               = type
        self.stomp_obj          = stomp_obj
        self.pmode              = None
        self.num_reqs           = 0
        self.busy_time          = 0
        self.last_dag_id        = None
        self.last_task_id       = None

        self.stats                            = {}
        self.stats['Tasks Serviced']          = 0
        self.stats['Tasks Serviced per Type'] = {}
        self.stats['Avg Resp Time']           = 0     # Overall for all tasks
        self.stats['Avg Resp Time per Type']  = {}    # Per task type
        self.stats['Met Deadline']            = 0     # Overall for all tasks
        self.stats['Met Deadline per Type']   = {}    # Per task type
        self.stats['Service Time per Type']   = {}    # Per task type
        self.stats['Lifetime per Type']       = {}    # Per task type

        self.reset()

        logging.debug('Server %d of type %s created' % (self.id, self.type))

    def reset(self):

        self.busy                   = False
        self.reserved               = False
        self.curr_service_time      = None
        self.curr_job_start_time    = None
        self.curr_job_end_time      = None
        self.last_usage_started_at  = None
        self.task                   = None
        self.curr_job_ptoks         = 0

    def communication_cost(self, task):
        # communication_cost[task.type][parent_server_type][self.server_type]
        noaffinity_time = 0
        for parent in task.parent_data:
            if parent[1]  == self.id and parent[0] == self.last_task_id and task.dag_id == self.last_dag_id:
                noaffinity_time             += 0
            else:
                parent_server_type          = self.stomp_obj.servers[parent[1]].type
                server_type = self.type
                if(parent_server_type.endswith("accel")):
                    parent_server_type = "accel"
                if(server_type.endswith("accel")):
                    server_type = "accel"
                noaffinity_time             += self.stomp_obj.params['simulation']['tasks'][task.type]['comm_cost'][parent_server_type][server_type]
                # noaffinity_time             += 0.25 * task.mean_service_time_dict[self.type]
        return float(noaffinity_time)

    def assign_task(self, sim_time, task, service_time_scale=None):
        self.stomp_obj.print("Assigning task to server {},{}".format(self.id, self.type))
        # At this moment, we know the target server where the task will run.
        # Therefore, we can compute the task's service time
        task_dag_id                     = task.dag_id
        task_tid                        = task.tid
        task_priority                   = task.priority
        task_deadline                   = task.deadline
        mean_service_time               = task.mean_service_time_dict[self.type]
        stdev_service_time              = task.stdev_service_time_dict[self.type]
        service_time                    = task.per_server_service_dict[self.type] # Use the per-server type service time, indexed by server_type
        if service_time_scale != None:
            service_time_new            = round(service_time * service_time_scale)
            # assert service_time == service_time_new, "==================xxxxxxxxxxxxxx=================="
            service_time = service_time_new
            # print("service_time=%u, service_time_scale=%u" % (service_time, service_time_scale))
        noaffinity_time                 = 0
        #service_time                     = int(round(numpy.random.normal(loc=mean_service_time, scale=stdev_service_time, size=1)))
        # Ensure that the random service time is a positive value...
        if (service_time <= 0):
            service_time = 1

        #### AFFINITY ####
        # Maintain dag_id + task id of last executed task
        # Calculate execution time based on if parent was last executed on the server
        ####
        # if self.last_dag_id != None:
        #     print("Server id: %d last DAG id and task id: %d,%d" % (self.id, self.last_dag_id, self.last_task_id))

        busy_servers = 0
        for server in self.stomp_obj.servers:
            if server.busy:
                busy_servers += 1

        contention_factor = 1
        if (self.stomp_obj.params['simulation']['contention']):
            contention_factor = self.stomp_obj.contention_factor[busy_servers]
        noaffinity_time = contention_factor * self.communication_cost(task)

        # print("Contention: %d Factor: %f No_affinity_time: %f" %(busy_servers, contention_factor, noaffinity_time))
        # else:
        #     for parent in task.parent_data:
        #         if parent[1]  == self.id and parent[0] == self.last_task_id and task_dag_id == self.last_dag_id:
        #             noaffinity_time             += 0
        #         else:
        #             noaffinity_time             += 0.25 * task.mean_service_time_dict[self.type]
                    # print("No Affinity for parent %lf" % (noaffinity_time))
        task.noaffinity_time = int(round(noaffinity_time))
        task.server_type = self.type
        task.task_service_time              = service_time + task.noaffinity_time
        # print("service_time=%u, task_service_time=%u" % (service_time, task.task_service_time))

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

        self.curr_job_ptoks                 = task.ptoks_used

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
    def assign_task_to_server(self, sim_time, tasks, dags_dropped, stomp_obj): pass

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

    def __init__(self, sharedObjs, stomp_params, sched_policy):
        self.env               = sharedObjs.env
        self.max_timesteps     = sharedObjs.max_timesteps
        self.tsched_eventq     = sharedObjs.tsched_eventq
        self.meta_eventq       = sharedObjs.meta_eventq
        self.global_task_trace = sharedObjs.global_task_trace
        self.tasks_completed   = sharedObjs.tasks_completed
        self.dags_dropped      = sharedObjs.dags_dropped
        self.drop_hint_list    = sharedObjs.drop_hint_list

        self.released_servers = MyPriorityQueue()

        self.params       = stomp_params
        self.meta         = None
        self.sched_policy = sched_policy
        self.working_dir  = self.params['general']['working_dir']
        self.basename     = self.params['general']['basename']
        self.num_tasks_generated = 0
        self.contention_factor = [1.00, 1.27, 1.40, 1.52, 1.69, 1.73, 1.97, 2.29, 2.38, 2.67, 2.84, 3.03, 3.25]
        self.time_since_last_completed = 0

        logging.basicConfig(level=eval('logging.' + self.params['general']['logging_level']),
                            format="%(message)s",
                            stream=sys.stdout)

        numpy.random.seed(self.params['general']['random_seed'])

        logging.info("CONFIGURATION:\n%s\n" % (self.params))  #pprint.pprint(self.params))

        self.tasks                            = []   # Main queue
        self.num_critical_tasks               = 0
        self.servers                          = []
        self.server_types                     = []
        self.tasks_to_servers                 = {}   # Maps task type to target servers

        self.intrace_server_order             = []

        self.ta_time                          = timedelta(microseconds = 0)
        self.to_time                          = timedelta(microseconds = 0)

        # Global stats
        self.stats                            = {}
        self.stats['Running Tasks']           = 0
        self.stats['Busy Servers']            = 0
        self.stats['Available Servers']       = {}
        self.stats['Tasks Generated']         = 0
        self.stats['Tasks Generated by META'] = 0
        self.stats['Tasks Serviced']          = 0
        self.stats['Tasks Serviced per Type'] = {}
        self.stats['Avg Resp Time']           = 0     # Overall for all tasks
        self.stats['Avg Resp Time per Type']  = {}    # Per task type
        self.stats['Met Deadline']            = 0     # Overall for all tasks
        self.stats['Met Deadline per Type']   = {}    # Per task type

        # Histograms
        self.bin_size                         = 1
        self.num_bins                         = 12
        self.stats['Queue Size Histogram']    = numpy.zeros(self.num_bins, dtype=int)  # N-bin histogram
        self.stats['Max Queue Size']          = 0

        self.task_trace_files                 = {}   # Per task type
        self.task_trace_file                  = open(self.working_dir + '/' + self.basename + '.global.trace.csv', 'w')
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

        self.task_assign_trace                = open(self.working_dir + '/' + self.basename + '.global.atrace.csv', 'w')
        self.task_assign_trace.write('%s\n\n' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.task_assign_trace.write("CONFIGURATION:\n%s\n" % (self.params))  #pprint.pprint(self.params))
        self.task_assign_trace.write('Time\tResponse time (avg)\n')

        self.init_servers()

        # IF user specified an input trace file then read that in here:
        self.random = 0
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

        self.action = self.env.process(self.run())
        self.last_size_change_time = self.env.now

    def print(self, string):
        pass
        # logging.info(bcolors.OKBLUE + "[%10ld][TSCHED] " % self.env.now + str(string) + bcolors.ENDC)

    def init_servers(self):
        for s_id in range(0, len(self.params['simulation']['servers'])):
            for server_type in self.params['simulation']['servers']:
                if(self.params['simulation']['servers'][server_type]['id'] == s_id):
                    self.server_types.append(server_type)
                    break

        id = 0
        for server_type in self.params['simulation']['servers']:
            if not server_type in self.stats['Available Servers']:
                self.stats['Available Servers'][server_type] = self.params['simulation']['servers'][server_type]['count']
            server_count = self.params['simulation']['servers'][server_type]['count']
            for i in range(0, server_count):
                self.servers.append(Server(id, server_type, self))
                id += 1
            #self.supported_servers.append(server_type)

    def release_server(self, server):
        # Update statistics
        task_type = server.task.type

        resp_time = (self.env.now - server.task.arrival_time)
        server.task.task_lifetime = resp_time
        # if self.env.now == 7302:
        #     print("Releasing server={},{}, task={}".format(server.id, server.type, server.task))
        # self.print("server {},{} task {} lifetime {}".format(server.id, server.type, server.task, server.task.task_lifetime))
        assert server.task.task_lifetime != None and server.task.task_lifetime > 0
        server.task.peid = server.id

        self.tasks_completed.put(server.task)
        # self.print("Scheduling meta event for {}".format(self.env.now))
        self.meta_eventq.put(self.env.now, events.TASK_COMPLETED)
        # self.print("TSCHED interrupting Meta")
        self.meta.action.interrupt()
        assert server.curr_job_ptoks != 0 and server.curr_job_ptoks != None

        # Return the freed up power tokens to the pool of available power tokens.
        if self.params['simulation']['pwr_mgmt']:
            self.sched_policy.avail_ptoks += server.curr_job_ptoks
        # logging.info('[%10d][%d.%d] restored %u ptoks, current available ptoks = %u, releasing server = %d' %
            # (self.sim_time, server.task.dag_id, server.task.tid, server.curr_job_ptoks,
            #  self.sched_policy.avail_ptoks, server.id)) #Aporva
        if self.params['simulation']['no_completed_activity_check']:
            self.time_since_last_completed = 0

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

        self.stats['Tasks Serviced']                     += 1
        self.stats['Tasks Serviced per Type'][task_type] += 1
        self.stats['Busy Servers']                       -= 1
        self.stats['Available Servers'][server.type]     += 1

        self.curr_job_ptoks = 0

        assert self.stats['Tasks Serviced'] != 0
        avg_resp_time = self.stats['Avg Resp Time'] / self.stats['Tasks Serviced']
        self.task_trace_file.write('%ld,%.1f,%d,%s,%d,%s,%d,%d,%d,%d,%d,%s,%d,%d,%d\n' % (
            self.env.now,
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
        self.task_trace_files[task_type].write('%ld\t%.1f\n' % (self.env.now, avg_resp_time))

        self.sched_policy.remove_task_from_server(self.env.now, server)

        # print("[%d] [%d,%d] Releasing server: %d" %(self.sim_time, server.task.dag_id, server.task.tid, server.id))
        server.reset()

    def print_stats(self):
        assert self.stats['Tasks Serviced'] != 0
        self.stats['Avg Resp Time'] /= self.stats['Tasks Serviced']

        # Final histogram update
        # self.print("queue_size = {}".format(len(self.tasks)))
        self.update_histogram(len(self.tasks))

        # Normalize histogram
        total_time = numpy.sum(self.stats['Queue Size Histogram'])
        pct_qsize = numpy.around(100 * self.stats['Queue Size Histogram'] / total_time, decimals=2)

        ##### DUMP STATISTICS TO STDOUT #####

        logging.info('\n==================== Simulation Statistics ====================')
        logging.info(' Total simulation time: %ld' % self.env.now)
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

        server = self.sched_policy.output_final_stats(self.env.now)

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
    def print_welcome(self):
        logging.info("""
 _____ _____ ________  _________
/  ___|_   _|  _  |  \/  || ___ \\
\ `--.  | | | | | | .  . || |_/ /
 `--. \ | | | | | | |\/| ||  __/
/\__/ / | | \ \_/ / |  | || |
\____/  \_/  \___/\_|  |_/\_|
        """)
        self.print("Starting simulation...")

    def update_histogram(self, queue_size):
        bin         = int(queue_size / self.bin_size)
        time_period = self.env.now - self.last_size_change_time
        if (self.stats['Max Queue Size'] < queue_size):
            self.stats['Max Queue Size'] = queue_size
        if (bin >= len(self.stats['Queue Size Histogram'])):
            bin = len(self.stats['Queue Size Histogram']) - 1
        self.stats['Queue Size Histogram'][bin] += time_period
        self.last_size_change_time = self.env.now

    def handle_task_arrival(self, task_arr_time, the_task):
        assert len(self.tasks) != self.params['simulation']['max_queue_size'], '[%10ld] Problem with finding an empty queue slot!' % (self.env.time)

        # self.print("queue_size = {}".format(len(self.tasks)))
        self.update_histogram(len(self.tasks))

        # Create and enqueue a new task
        # Select the "type" of task to create
        # NOTE: self.global_task_trace is used for EITHER an input trace or pre-gen arrival trace behavior

        the_task.trace_id = self.num_tasks_generated

        if (the_task.priority > 1):
            self.num_critical_tasks += 1

        self.tasks.append(the_task)
        self.stats['Tasks Generated'] += 1

        if (self.output_trace_file):
            self.output_trace.write('%d,%s,%d,%d,%d,%d,%d,%s\n' % (self.env.now, task_type, the_task.dag_id, the_task.tid, the_task.size, the_task.priority, the_task.deadline, ','.join(map(str, the_task.per_server_services))))

        task_type = the_task.type
        if not task_type in self.stats['Avg Resp Time per Type']:
            self.stats['Avg Resp Time per Type'][task_type]  = 0
            self.stats['Met Deadline per Type'][task_type]   = 0
            self.stats['Tasks Serviced per Type'][task_type] = 0

            trace_filename = self.working_dir + '/' + self.basename + '.' + task_type + '.' + self.params['simulation']['sched_policy_module'].split('.')[-1] + '.trace.csv'
            self.task_trace_files[task_type] = open(trace_filename, 'w')

            self.task_trace_files[task_type].write('%s\n\n' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            self.task_trace_files[task_type].write("CONFIGURATION:\n%s\n" % (self.params))  #pprint.pprint(self.params))
            self.task_trace_files[task_type].write('Time\tResponse time (avg)\n')

        self.num_tasks_generated += 1

    def schedule_avail_task(self):
        if not self.tasks:
            return
        free_server_count = 0
        for server in self.servers:
            if server.busy == False:
                free_server_count += 1

        # self.print("free_server_count {}".format(free_server_count))
        for x in range(free_server_count):
            if not self.tasks:
                return
            server = self.sched_policy.assign_task_to_server(self.env.now, self.tasks, self.dags_dropped, self)

            # self.print("Task NOT assigned to server")
            if server == None:
                continue
            self.ta_time = self.sched_policy.ta_time
            self.to_time = self.sched_policy.to_time

            assert server.task != None
            self.released_servers.put(server.curr_job_end_time, server)

            self.tsched_eventq.put(server.curr_job_end_time, events.SERVER_FINISHED)

            self.stats['Running Tasks']                  += 1
            self.stats['Busy Servers']                   += 1
            self.stats['Available Servers'][server.type] -= 1

            self.task_assign_trace.write('%ld,%d,%s,%d,%s,%d,%d,%d\n' % (self.env.now, server.task.trace_id, server.task.type, server.id, server.type, server.curr_job_start_time, server.curr_service_time, server.curr_job_end_time))

            self.update_histogram(len(self.tasks) + 1)  # +1 because the task was already removed

    def run(self):
        self.print_welcome()
        self.tsched_eventq.put(self.max_timesteps, events.SIM_LIMIT)

        # This is because some scheduling policies may need to know about
        # the existent servers in order to make scheduling decisions
        self.sched_policy.init(self.servers, self.stats, self.params)

        # STOMP variables are initialized, wait for Meta to start
        self.env.all_of([self.meta.action])

        event_count_arrival = 0
        event_count_release = 0
        sim_count = 0

        # wait for Meta to interrupt for first event processing
        try:
            yield self.env.timeout(self.max_timesteps)
        except simpy.Interrupt:
            pass

        # running event loop
        while True:
            tick, event = yield from handle_event(self.env, self.tsched_eventq)
            message_decode_event(self, event)

            if event == events.TASK_ARRIVAL:
                # global_task_trace is a priority queue of tasks (sorted by
                # arrival time) that are ready to be executed
                assert not self.global_task_trace.empty()
                task_arr_time, the_task = self.global_task_trace.get() # will block if empty
                self.handle_task_arrival(task_arr_time, the_task)

                # task coalescing logic - coalesce all tasks into self.tasks
                # that arrived at the same time
                # check if next eventq event is TASK_ARRIVAL and time of
                # event is same as env.now
                # if yes, continue without scheduling the task
                tick, event = self.tsched_eventq.peek()
                if event == events.TASK_ARRIVAL and tick == self.env.now:
                    continue

                # the last event in the event queue for the current tick is
                # responsible for scheduling the SCHEDULE_TASK event
                assert self.tasks
                next_tick, next_event = self.tsched_eventq.peek()
                if next_tick != self.env.now:
                    self.tsched_eventq.put(self.env.now, events.SCHEDULE_TASK)
            elif event == events.SCHEDULE_TASK:
                assert self.tasks
                self.schedule_avail_task()
            elif event == events.SERVER_FINISHED:
                assert not self.released_servers.empty()
                curtick, next_serv_end = self.released_servers.get()
                assert curtick == self.env.now
                assert next_serv_end.task != None
                self.release_server(next_serv_end)

                self.stats['Running Tasks'] -= 1

                logging.debug('[%10ld] Server finished' % (self.env.now))
                logging.debug('             Running tasks: %d, busy servers: %d, waiting tasks: %d' % (self.stats['Running Tasks'], self.stats['Busy Servers'], len(self.tasks)))

                # if there are ready tasks sitting in the queue then
                # schedule the SCHEDULE_TASK event if the is also the last
                # event in the event queue for the current tick
                if self.tasks:
                    next_tick, next_event = self.tsched_eventq.peek()
                    if next_tick != self.env.now:
                        self.tsched_eventq.put(self.env.now, events.SCHEDULE_TASK)
            elif event == events.META_DONE:
                # self.print("META is done, exiting")
                break
            elif event == events.SIM_LIMIT:
                assert False
            else:
                raise NotImplementedError

            if self.params['simulation']['no_completed_activity_check']:
                self.time_since_last_completed += 1
                if self.time_since_last_completed > self.params['simulation']['progress_intvl_f'] * \
                    self.params['simulation']['mean_arrival_time'] * \
                    self.params['simulation']['arrival_time_scale']:
                    print('[%10ld] WARNING: No completed activity since last %u timesteps' %
                        (self.sim_time, self.time_since_last_completed), file=sys.stderr)

                sim_count += 1

        # Close task trace files
        self.task_trace_file.close()
        self.task_assign_trace.close()

        for task in self.task_trace_files:
            self.task_trace_files[task].close()

        if (self.output_trace_file):
            self.output_trace.close()

        self.print("STOMP simulation complete")
        self.print_stats()
