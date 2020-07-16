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
#  This policy effectively attempts to provide the least utilization time 
#  (overall) for all the servers during the run.  For highly skewed
#  mean service times, this policy may delay the start time of a task until
#  a fast server is available.

from stomp import BaseSchedulingPolicy
import logging
from datetime import datetime, timedelta 

class SchedulingPolicy(BaseSchedulingPolicy):

    def init(self, servers, stomp_stats, stomp_params):
        
        self.stomp_stats  = stomp_stats
        self.stomp_params = stomp_params
        self.servers      = servers
        self.n_servers    = len(servers)
        self.ta_time      = timedelta(microseconds=0)
        self.to_time      = timedelta(microseconds=0)


    def assign_task_to_server(self, sim_time, tasks, dags_dropped, drop_hint_list, num_critical_tasks):

        if (len(tasks) == 0):
            # There aren't tasks to serve
            return None    
        
        task = tasks[0]
        logging.debug('[%10ld] Scheduling task %s' % (sim_time, task.type))
        
        # Compute execution times for each target server, factoring in
        # the remaining execution time of tasks already running.
        target_servers = []
        for server in self.servers:
            
            if (server.type in task.mean_service_time_dict):
                
                mean_service_time   = task.mean_service_time_dict[server.type]
                if (server.busy):
                    remaining_time  = server.curr_job_end_time - sim_time
                else:
                    remaining_time  = 0
                actual_service_time = mean_service_time + remaining_time
                
                target_servers.append(actual_service_time)
            
            else:
                target_servers.append(float("inf"))
        
        # Look for the server with smaller actual_service_time
        # and check if it's available
        server_idx = target_servers.index(min(target_servers))

        if (not self.servers[server_idx].busy):
            # Pop task in queue's head and assign it to server
            self.servers[server_idx].assign_task(sim_time, tasks.pop(0))
            return self.servers[server_idx]
        else:
            return None


    def remove_task_from_server(self, sim_time, server):
        pass

    def output_final_stats(self, sim_time):
        pass
