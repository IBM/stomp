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

# SCHEDULING POLICY DESCRIPTION:
#  This scheduling policy tries to schedule the task at the head of the
#  queue into the queue that will result in the earliest estimated
#  completion time for this task (factoring in the given start time
#  of the task taking into account the current busy status of a server).
#  IF that task does not immeidately "issue" to the selected server
#   (i.e. that server is "busy") then it considers the next task on the task list,
#   and continues to do so until it has checked a number of tasks equal to
#   the max_task_depth_to_check parm (defined below).
#  This policy effectively attempts to provide the least utilization time 
#  (overall) for all the servers during the run.  For highly skewed
#  mean service times, this policy may delay the start time of a task until
#  a fast server is available.
# This is the first example that includes "issue" of tasks other than the
#  one at the head of the queue...
#


from stomp import BaseSchedulingPolicy
import logging
import numpy
from datetime import datetime, timedelta 

max_task_depth_to_check = 10

class SchedulingPolicy(BaseSchedulingPolicy):

    def init(self, servers, stomp_stats, stomp_params):
        self.bin_size =  1
        self.num_bins = 12
        self.stomp_stats  = stomp_stats
        self.stomp_params = stomp_params
        self.servers      = servers
        self.n_servers    = len(servers)
        self.stats                            = {}
        self.stats['Task Issue Posn'] = numpy.zeros(self.num_bins, dtype=int)  # N-bin histogram
        self.ta_time      = timedelta(microseconds=0)
        self.to_time      = timedelta(microseconds=0)


    def assign_task_to_server(self, sim_time, tasks, dags_dropped, stomp_obj):
        
        for task in tasks:
            if task.dag_id in dags_dropped:
                # print("Removing dropped dag")
                tasks.remove(task)
                if (task.priority > 1):
                    stomp_obj.num_critical_tasks -= 1

        if (len(tasks) == 0):
            # There aren't tasks to serve
            return None  

        if (len(tasks) > max_task_depth_to_check):
            window_len = max_task_depth_to_check
        else:
            window_len = len(tasks)
			
        start = datetime.now()


        for t in tasks:
            max_time = 0
            min_time = 100000
            num_servers = 0
            for server in self.servers:
                if (server.type in t.per_server_service_dict):
                    service_time   = t.per_server_service_dict[server.type]
                    if(max_time < float(service_time)):
                        max_time = float(service_time)
                    if(min_time > float(service_time)):
                        min_time = float(service_time)
                    num_servers += 1


            if ((t.deadline -(sim_time-t.arrival_time) - (max_time)) < 0):
                if (t.priority > 1):
                    if((t.deadline -(sim_time-t.arrival_time) - (min_time)) >= 0):
                        slack = 1 + (t.deadline - (sim_time-t.arrival_time) - (min_time))
                        t.rank = int((100000 * (1000000*t.priority))/slack)
                        t.rank_type = 4
                        # print("[%d] [%d,%d,%d] Min deadline exists deadline:%d, slack: %d, atime:%d, max_time: %d, min_time: %d" % 
                        #     (sim_time, t.dag_id, t.tid, t.priority, t.deadline, slack, t.arrival_time, max_time, min_time))
                        
                    else:
                        slack = 1 - 0.99/((sim_time-t.arrival_time) + min_time - t.deadline)
                        t.rank = int((100000 * (10000000*t.priority))/slack)
                        t.rank_type = 5
                        # print("[%d] [%d,%d,%d] Deadline passed deadline:%d, slack: %d, atime:%d, max_time: %d, min_time: %d" % 
                        #     (sim_time, t.dag_id, t.tid, t.priority, t.deadline, slack, t.arrival_time, max_time, min_time))
                        
                else:
                    if (stomp_obj.num_critical_tasks > 0 and self.stomp_params['simulation']['drop'] == True):
                        # print("[%d] [%d,%d,%d] Critical tasks and min deadline exists deadline:%d, atime:%d, max_time: %d, min_time: %d" % 
                        #     (sim_time, t.dag_id, t.tid, t.priority, t.deadline, t.arrival_time, max_time, min_time))
                        t.rank = 0
                        stomp_obj.drop_hint_list.append(t.dag_id)
                        # print("[ID: %d] A hinting from task scheduler" %(t.dag_id))
                    else:
                        if((t.deadline -(sim_time-t.arrival_time) - (min_time)) >= 0):
                            slack = 1 + (t.deadline - (sim_time-t.arrival_time) - (min_time))
                            t.rank = int((100000 * (100*t.priority))/slack)
                            t.rank_type = 1
                            # print("B", t.rank)
                            # print("[%d] [%d,%d,%d] Min deadline exists deadline:%d, slack: %d, atime:%d, max_time: %d, min_time: %d" % 
                            #     (sim_time, t.dag_id, t.tid, t.priority, t.deadline, slack, t.arrival_time, max_time, min_time))
                            
                        else:
                            # print("[%d] [%d,%d,%d] Min deadline doesnt exist/priority 1 type:%s with no max deadline:%d, atime:%d, max_time: %d, min_time: %d" % 
                            #     (sim_time, t.dag_id, t.tid, t.priority, t.type, t.deadline,t.arrival_time, max_time, min_time))
                            if(self.stomp_params['simulation']['drop']== True):
                                t.rank = 0
                                stomp_obj.drop_hint_list.append(t.dag_id)
                                # print("[ID: %d] B hinting from task scheduler" %(t.dag_id))

                            else:
                                slack = 1 - 0.99/((sim_time-t.arrival_time) + min_time - t.deadline)
                                t.rank = int((100000 * (1*t.priority))/slack)
                                t.rank_type = 0
                                # print("A", t.rank)


            else:
                slack = 1 + (t.deadline - (sim_time-t.arrival_time) - (max_time))
                if (t.priority > 1):
                    t.rank = int((100000 * (10000*t.priority))/slack)
                    t.rank_type = 3
                else:
                    t.rank = int((100000 * 1000*(t.priority))/slack)
                    t.rank_type = 2
                # print("[%d] [%d,%d,%d] Max deadline exists deadline:%d, slack: %d, atime:%d, max_time: %d, min_time: %d" % 
                #     (sim_time, t.dag_id, t.tid, t.priority,t.deadline, slack, t.arrival_time, max_time, min_time))

            # if (self.stomp_params['simulation']['drop'] == True and stomp_obj.num_critical_tasks > 0 and t.priority == 1):
            #     # print("[%d] [%d,%d,%d] Critical tasks and min deadline exists deadline:%d, atime:%d, max_time: %d, min_time: %d" % 
            #     #     (sim_time, t.dag_id, t.tid, t.priority, t.deadline, t.arrival_time, max_time, min_time))
            #     t.rank = 0
            #     drop_hint_list.append(t.dag_id)
            #     print("[ID: %d] C hinting from task scheduler" %(t.dag_id))

        # tasks.sort(key=lambda task: (task.rank), reverse=True)
        # print(tasks)
        
        tasks.sort(key=lambda task: (task.rank_type,task.rank), reverse=True)
        

        # print("Start")
        # for t in tasks:
        #     print("[%d] [%d,%d,%d][%d] rank: %d deadline:%d, atime:%d, PSI: %s" % (sim_time, t.dag_id, t.tid, t.priority, t.rank_type, t.rank, t.deadline, t.arrival_time, t.possible_server_idx))
            
        # print("End")

        # x = []
        # for server in self.servers:
        #     if server.busy:
        #         x.append(server.id);

        # print("busy server", x)


        end = datetime.now()
        self.to_time += end - start
        # print(("TO: %d")%(self.to_time.microseconds))
        window = tasks[:window_len]
        
        # out = str(sim_time) + ","
        # ii = 0
        # for w in window:
        #     out += (("%d, atime: %d, dead: %d, rank: %d, priority: %d,") % (ii,w.arrival_time,w.deadline,w.rank,w.priority))
        #     ii += 1
        # print(out)
            
        tidx = 0;
        
        start = datetime.now()       
        for task in window:
            # logging.debug('[%10ld] Attempting to schedule task %2d : %s' % (sim_time, tidx, task.type))
        
            # Compute execution times for each target server, factoring in
            # the remaining execution time of tasks already running.
            target_servers = []
            for server in self.servers:

                # print("[%d] [%d.%d] Params: task.priority = %d server.type = %s stomp_obj.num_critical_tasks = %d" 
                #     % (sim_time, task.dag_id, task.tid, task.priority, server.type, stomp_obj.num_critical_tasks))
                # if ((task.priority == 1 and (server.type == "cpu_core")) or task.priority > 1):
                if ((task.priority == 1 and (server.type == "cpu_core" or stomp_obj.num_critical_tasks <= 0)) or task.priority > 1):
                        
                    # logging.debug('[%10ld] Checking server %s' % (sim_time, server.type))
                    if (server.type in task.mean_service_time_dict):
                    
                        mean_service_time   = task.mean_service_time_dict[server.type]
                        if (server.busy):
                            remaining_time  = server.curr_job_end_time - sim_time
                            for stask in window:
                                if(stask == task):
                                    break
                                if (self.servers.index(server) == stask.possible_server_idx):
                                    remaining_time  += stask.mean_service_time_dict[server.type]
                        else:
                            remaining_time  = 0
                        actual_service_time = mean_service_time + remaining_time
                    
                        # print('[%10ld] [%d.%d.%d] Server:%d %s : mst %d ast %d ' % (sim_time, task.dag_id, task.tid, task.priority, server.id, server.type, mean_service_time, actual_service_time))
                        target_servers.append(actual_service_time)
                    else:
                        target_servers.append(float("inf"))
                else:
                    target_servers.append(float("inf"))
        
            # Look for the server with smaller actual_service_time
            # and check if it's available
            server_idx = target_servers.index(min(target_servers))
            # if (task.priority == 1 and self.servers[server_idx].type != "cpu_core"):
            #     print('[%10ld] [%d.%d] Assertion failed %2d %s to server %2d %s' % (sim_time, task.dag_id, task.tid, tidx, task.type, server_idx, self.servers[server_idx].type))
            #     assert(False)

            if (not self.servers[server_idx].busy):
                # Pop task in queue and assign it to server
                tasks.remove(task)
                if (task.priority > 1):
                    stomp_obj.num_critical_tasks -= 1
                # print('[%10ld] [%d.%d] Scheduling task %2d %s to server %2d %s' % (sim_time, task.dag_id, task.tid, tidx, task.type, server_idx, self.servers[server_idx].type))
                
                self.servers[server_idx].assign_task(sim_time, task)
                bin = int(tidx / self.bin_size)        
                if (bin >= len(self.stats['Task Issue Posn'])):
                    bin = len(self.stats['Task Issue Posn']) - 1
                # logging.debug('[          ] Set BIN from %d / %d to %d vs %d = %d' % (tidx, self.bin_size, int(tidx / self.bin_size), len(self.stats['Task Issue Posn']), bin))
                self.stats['Task Issue Posn'][bin] += 1
                end = datetime.now()
                self.ta_time += end - start
                # print(("TA: %d")%(self.ta_time.microseconds))
                return self.servers[server_idx]
            else:
                task.possible_server_idx = server_idx
            tidx += 1  # Increment task idx
            # if (tidx >= max_task_depth_to_check):
            #     break
        end = datetime.now()
        self.ta_time += end - start
        # print(("TA: %d")%(self.ta_time.microseconds))
        return None

    def remove_task_from_server(self, sim_time, server):
        pass


    def output_final_stats(self, sim_time):
        logging.info('   Task Issue Position: %s' % (', '.join(map(str,self.stats['Task Issue Posn']))))
        idx = 0;
        bin = 0;
        logging.info('         %4s  %10s' % ("Bin", "Issues"))
        c_time = 0
        c_pct_time = 0
        for count in self.stats['Task Issue Posn']:
            sbin = str(bin)
            logging.info('         %4s  %10d' % (sbin, count))
            idx += 1
            if (idx < (self.num_bins - 1)):
                bin += self.bin_size
            else:
                bin = ">" + str(bin)
        logging.info('')

