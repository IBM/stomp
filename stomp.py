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
from abc import ABCMeta, abstractmethod
import numpy
import pprint
import sys
import operator
import logging
import datetime


###############################################################################
# This class represents a 'task' that is processed in the queuing system.     #
# Its 'service time' is determined from a specified probability distribution  #
# (exponential, normal or uniform).                                           #
###############################################################################
class Task:
    
    def __init__(self, sim_time, id, type, params):
        
        # Obtain a service time for the new task
        #service_time = numpy.random.normal(loc=mean, scale=stdev, size=1)

        self.type                    = type
        self.mean_service_time_dict  = params['mean_service_time']
        self.mean_service_time_list  = sorted(params['mean_service_time'].items(), key=operator.itemgetter(1)) 
        self.stdev_service_time_dict = params['stdev_service_time']
        self.stdev_service_time_list = sorted(params['stdev_service_time'].items(), key=operator.itemgetter(1))
        self.arrival_time            = sim_time
        #self.curr_arrival_time      = sim_time
        self.departure_time          = None
        self.task_service_time       = None  # To be set upon scheduling, since it depends on the target server
        self.task_lifetime           = None  # To be set upon finishing; includes time span from arrival to departure
        self.trace_id                = id
        #self.run_pos                = 0
        self.wpower                  = None
        self.current_time            = 0

    def __str__(self):
        return ('Task ' + str(self.trace_id) + ' ( ' + self.type + ' ) ' + str(self.arrival_time))

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

        self.stats                            = {}
        self.stats['Tasks Serviced']          = 0
        self.stats['Tasks Serviced per Type'] = {}
        self.stats['Avg Resp Time']           = 0     # Overall for all tasks
        self.stats['Avg Resp Time per Type']  = {}    # Per task type
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
        mean_service_time                = task.mean_service_time_dict[self.type]
        stdev_service_time               = task.stdev_service_time_dict[self.type]
        service_time                     = int(round(numpy.random.normal(loc=mean_service_time, scale=stdev_service_time, size=1)))
        # Ensure that the random service time is a positive value...
        if (service_time <= 0): 
            service_time = 1;
        task.task_service_time           = service_time
        
        self.busy                        = True
        self.curr_service_time           = task.task_service_time
        self.curr_job_start_time         = sim_time
        self.curr_job_end_time           = self.curr_job_start_time + self.curr_service_time
        self.curr_job_end_time_estimated = self.curr_job_start_time + mean_service_time
        self.last_usage_started_at       = sim_time
        self.num_reqs                    += 1
        self.task                        = task
        
        self.busy_time                   += self.curr_service_time
    
    
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
    def assign_task_to_server(self, sim_time, tasks): pass

    @abstractmethod
    def remove_task_from_server(self, sim_time, server): pass
    
    
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

    
    def __init__(self, stomp_params, sched_policy):
        
        self.params       = stomp_params
        self.sched_policy = sched_policy
        self.working_dir  = self.params['general']['working_dir']
        self.basename     = self.params['general']['basename']
        self.num_tasks_generated = 0

        logging.basicConfig(level=eval('logging.' + self.params['general']['logging_level']), format="%(message)s")
        
        numpy.random.seed(self.params['general']['random_seed'])
        
        #pprint.pprint(self.params)
        logging.info("CONFIGURATION:\n%s\n" % (self.params))  #pprint.pprint(self.params))
        
        self.tasks                            = []   # Main queue
        self.servers                          = []
        self.tasks_to_servers                 = {}   # Maps task type to target servers
        #self.supported_servers               = []

        self.sim_time                         = 0    # Simulation time
        
        # Global stats
        self.stats                            = {}
        self.stats['Running Tasks']           = 0
        self.stats['Busy Servers']            = 0
        self.stats['Available Servers']       = {}
        self.stats['Tasks Generated']         = 0
        self.stats['Tasks Serviced']          = 0
        self.stats['Tasks Serviced per Type'] = {}
        self.stats['Avg Resp Time']           = 0     # Overall for all tasks
        self.stats['Avg Resp Time per Type']  = {}    # Per task type
        
        # Histograms
        self.bin_size                         = 1
        self.num_bins                         = 12
        self.last_size_change_time            = self.sim_time
        self.stats['Queue Size Histogram']    = numpy.zeros(self.num_bins, dtype=int)  # N-bin histogram
        self.stats['Max Queue Size']          = 0
        
        self.task_trace_files                 = {}   # Per task type
        self.task_trace_file                  = open(self.working_dir + '/' + self.basename + '.global.trace', 'w')
        
        self.task_trace_file.write('%s\n\n' % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        self.task_trace_file.write("CONFIGURATION:\n%s\n" % (self.params))  #pprint.pprint(self.params))
        self.task_trace_file.write('Time\tResponse time (avg)\n')

        self.init_servers()

        # IF user specified an input trace file then read that in here:
        self.arrival_trace = []
        self.input_trace_file = stomp_params['general']['input_trace_file']
        self.output_trace_file = stomp_params['general']['output_trace_file']

        self.pre_gen_arrivals = stomp_params['general']['pre_gen_arrivals']

        if (self.input_trace_file and self.pre_gen_arrivals):
            logging.info('WARNING: both an input task arrival trace file and pre-gen arrivals options specified; using the input trace\n')
            
        if (self.input_trace_file):
            in_trace_name = self.working_dir + '/' + self.input_trace_file
            with open(in_trace_name, 'r') as input_trace:
                line_count = 0;
                for line in input_trace.readlines():
                    tmp = line.strip().split(',')
                    try:
                        self.arrival_trace.append((int(tmp[0]),tmp[1]));
                    except:
                        logging.info('Bad line in arrival trace file: %d : %s' % (line_count, tmp))
                    line_count += 1
        elif (self.pre_gen_arrivals):
            # create an a-priori list of tasks at times...
            a_task_time = 0;
            a_task_num = 0;
            while (a_task_num < self.params['simulation']['max_tasks_simulated']):
                task = numpy.random.choice(list(self.params['simulation']['tasks'])) 
                self.arrival_trace.append((a_task_time, task))
                a_task_time = int(round(a_task_time + numpy.random.exponential(scale=self.params['simulation']['mean_arrival_time'], size=1)))
                a_task_num = a_task_num + 1;
                
        if (self.output_trace_file):
            out_trace_name = self.working_dir + '/' + self.output_trace_file
            logging.info('Generating output trace file to %s' % (out_trace_name))
            self.output_trace = open(out_trace_name, 'w')
        
    


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
        # NOTE: self.arrival_trace is used for EITHER an input trace or pre-gen arrival trace behavior
        if (self.arrival_trace):
            tmp = self.arrival_trace.pop(0)
            task = tmp[1];
            logging.debug('[ %10ld ] Setting next task type from TRACE to %s' % (self.sim_time, task))
        else:
            task = numpy.random.choice(list(self.params['simulation']['tasks'])) 
            #logging.debug("NEW_TASK from %s\n" % list(self.params['simulation']['tasks']))
            #logging.debug("%s\n" % task)
        #task = Task(self.sim_time, self.params['simulation']['mean_service_time'], self.params['simulation']['stdev_service_time'])
        #self.tasks.append(task)
        self.tasks.append(Task(self.sim_time, task_num, task, self.params['simulation']['tasks'][task]))
        self.stats['Tasks Generated'] += 1

        if (self.output_trace_file):
            self.output_trace.write('%d,%s\n' % (self.sim_time, task))

                
        if not task in self.stats['Avg Resp Time per Type']:
            self.stats['Avg Resp Time per Type'][task]  = 0
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
        self.task_trace_file.write('%ld\t%.1f\n' % (self.sim_time, avg_resp_time))

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
        
        logging.info(' Response time (avg):')
        logging.info('   %12s : %8.2f over %8d tasks' % ("global", self.stats['Avg Resp Time'], self.stats['Tasks Serviced']))
        for task in self.stats['Avg Resp Time per Type']:
            if (self.stats['Tasks Serviced per Type'][task] > 0):
                logging.info('   %12s : %8.2f over %8d tasks' % (task, self.stats['Avg Resp Time per Type'][task]/self.stats['Tasks Serviced per Type'][task], self.stats['Tasks Serviced per Type'][task]))
            else:
                logging.info('   %12s : %8,2f over %8d tasks' % (task, 0.0, 0))
        logging.info('')

        logging.info(' Serfver Response time (avg):')
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
        logging.info('   Queue size Pct time: bin size, %d , max In Queue, %d , %s' % (self.bin_size, self.stats['Max Queue Size'],', '.join(map(str,self.stats['Queue Size Histogram']))))
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
                logging.info('   Server %3d : %12s : Avg %8.2f vs %8.3f : StDev %8.2f vs %8.3f : over %8d tasks' % (server.id, task,
                                                                                                                    avg,  self.params['simulation']['tasks'][task]['mean_service_time'][server.type],
                                                                                                                    #stdv, (self.params['simulation']['tasks'][task]['stdev_service_time'][server.type] * self.params['simulation']['tasks'][task]['mean_service_time'][server.type]),
                                                                                                                    stdv, self.params['simulation']['tasks'][task]['stdev_service_time'][server.type],
                                                                                                                    len(server.stats['Service Time per Type'][task])))
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
                    logging.info('   %12s : %12s : Avg %8.2f vs %8.3f : StDev %8.2f vs %8.3f : over %8d tasks' % (server_type, task_type,
                                                                                                                  avg,  self.params['simulation']['tasks'][task_type]['mean_service_time'][server_type],
                                                                                                                  stdv, self.params['simulation']['tasks'][task_type]['stdev_service_time'][server_type],
                                                                                                                  sden))

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
        while ((self.stats['Tasks Generated'] < self.params['simulation']['max_tasks_simulated']) or
              (len(self.tasks) > 0) or            # There are tasks in the queue, waiting to be served
              (self.stats['Busy Servers'] > 0)):  # There are tasks being served in the servers
        
            # Main duty loop: handle whichever simulation event occurs
            # earliest, then revert here in next iteration of main loop

            ######################################################################
            # 1) Determine next event to handle                                  #
            ######################################################################
            if (self.params['simulation']['power_mgmt_enabled'] and
               ((self.next_power_mgmt_time <= self.next_cust_arrival_time) or (self.stats['Tasks Generated'] >= self.params['simulation']['max_tasks_simulated'])) and
               (self.next_power_mgmt_time <= self.next_serv_end_time)):
                
                # Next event is a power management event
                next_event = STOMP.E_PWR_MGMT
            
            elif ((self.stats['Tasks Generated'] < self.params['simulation']['max_tasks_simulated']) and
                 ((self.next_cust_arrival_time <= self.next_power_mgmt_time) or not self.params['simulation']['power_mgmt_enabled']) and
                 ((self.next_cust_arrival_time <= self.next_serv_end_time) or (self.stats['Tasks Generated'] >= self.params['simulation']['max_tasks_simulated']))):
                
                # Next event is a task arrival
                next_event = STOMP.E_TASK_ARRIVAL
            
            else:
                assert (self.next_serv_end_time <= self.next_power_mgmt_time) or not self.params['simulation']['power_mgmt_enabled']
                assert (self.next_serv_end_time <= self.next_cust_arrival_time) or (self.stats['Tasks Generated'] >= self.params['simulation']['max_tasks_simulated'])
        
                # Next event is a server finishing the execution of its assigned task
                next_event = STOMP.E_SERVER_FINISHES
        

            ######################################################################
            # 2) Handle the event                                                #
            ######################################################################
            if (next_event == STOMP.E_PWR_MGMT):
                if (self.next_power_mgmt_time < self.sim_time):
                    logging.info('WARNING: Time Moving Backward: sim_time %ld but smaller next_power_mgmt_time %ld' % (self.sim_time, self.next_power_mgmt_time))
                # Manage power...
                self.sim_time = self.next_power_mgmt_time
                logging.warning('[%10ld] Power management not yet supported...' % (self.sim_time))
        
            elif (next_event == STOMP.E_TASK_ARRIVAL):
                if (self.next_cust_arrival_time < self.sim_time):
                    logging.info('WARNING: Time Moving Backward: sim_time %ld but smaller next_cust_arrival_time %ld' % (self.sim_time, self.next_cust_arrival_time))
                
                # Customer (task) arrival...
                self.sim_time = self.next_cust_arrival_time
                
                # Add task to queue
                if (self.generate_n_enqueue_new_task(self.num_tasks_generated)):
                    self.num_tasks_generated += 1
                    if (self.arrival_trace):
                        tmp = self.arrival_trace[0]
                        self.next_cust_arrival_time = tmp[0]
                        logging.debug('[ %10ld ] Setting next task arrival time from TRACE to %d ( %s )' % (self.sim_time, self.next_cust_arrival_time, tmp[1]))
                    else:
                        self.next_cust_arrival_time = int(round(self.sim_time + numpy.random.exponential(scale=self.params['simulation']['mean_arrival_time'], size=1)))

                logging.debug('[ %10ld ] Task enqueued. Next task will arrive at time %ld' % (self.sim_time, self.next_cust_arrival_time))
                logging.debug('               Running tasks: %d, busy servers: %d, waiting tasks: %d' % (self.stats['Running Tasks'], self.stats['Busy Servers'], len(self.tasks)))
        
                
            elif (next_event == STOMP.E_SERVER_FINISHES):
                if (self.next_serv_end_time < self.sim_time):
                    logging.info('WARNING: Time Moving Backward: sim_time %ld but smaller next_serv_end_time %ld' % (self.sim_time, self.next_serv_end_time))
                    

                # Service completion (next_cust_arrival_time >= next_serv_end_time)
                self.sim_time = self.next_serv_end_time
        
                assert(not self.next_serv_end is None);
                self.release_server(self.next_serv_end)
                self.stats['Running Tasks'] -= 1

                logging.debug('[%10ld] Server finished' % (self.sim_time))
                logging.debug('             Running tasks: %d, busy servers: %d, waiting tasks: %d' % (self.stats['Running Tasks'], self.stats['Busy Servers'], len(self.tasks)))
        
                
            ######################################################################
            # 3) Make scheduling decisions                                       #
            ######################################################################
            
            server = self.sched_policy.assign_task_to_server(self.sim_time, self.tasks)
            #print(server)
            if server is not None:
                if server.curr_job_end_time < self.next_serv_end_time:
                    self.next_serv_end_time = server.curr_job_end_time
                    self.next_serv_end      = server

                self.stats['Running Tasks']                  += 1
                self.stats['Busy Servers']                   += 1
                self.stats['Available Servers'][server.type] -= 1

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

                logging.debug('[ %10ld ] Task %d scheduled in server %d ( %s ) until %d' % (self.sim_time, server.task.trace_id, server.id, server.type, server.curr_job_end_time))
                logging.debug('               Running tasks: %d, busy servers: %d, waiting tasks: %d' % (self.stats['Running Tasks'], self.stats['Busy Servers'], len(self.tasks)))
                logging.debug('               Avail: %s' % (', '.join(['%s: %s' % (key, value) for (key, value) in self.stats['Available Servers'].items()])))



        # Close task trace files
        for task in self.task_trace_files:
            self.task_trace_files[task].close()

        if (self.output_trace_file):
            self.output_trace.close()
