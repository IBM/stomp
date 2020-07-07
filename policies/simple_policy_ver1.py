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
#  queue ONLY in its best scheduling option (i.e. fastest server).
#  If a queue from the best scheduling option isn't available, the task
#  remains in the queue (i.e. no other less-optimal server platform is
#  considered).

import logging
from stomp import BaseSchedulingPolicy
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
        
        # Determine task's best scheduling option (target server)
        target_server_type = tasks[0].mean_service_time_list[0][0]
        # logging.info(tasks)
        # logging.info('POL: %d,%s,%d,%d,%d,%d,%s' % (sim_time, tasks[0].type, tasks[0].dag_id, tasks[0].tid, tasks[0].priority, tasks[0].deadline, ','.join(map(str, tasks[0].per_server_services))))
        # if(sim_time != tasks[0].arrival_time):
        #     logging.info("CHECK")     
        # Look for an available server to process the task
        for server in self.servers:
    
            if (server.type == target_server_type and not server.busy):

                # Pop task in queue's head and assign it to server
                # print('SERVER_ASSIGNED: %d,%s,%d,%s,%d,%d\n' % (sim_time, server.type, server.id, tasks[0].type, tasks[0].dag_id, tasks[0].tid)) #Aporva
                # for server_stat in self.servers:
                    # if (server_stat.busy):
                    #     print('BUSY: %s,%d,%s' % (server_stat.type, server_stat.id, server_stat.busy))
                server.assign_task(sim_time, tasks.pop(0))

                return server
                
        return None


    def remove_task_from_server(self, sim_time, server):
        pass

    def output_final_stats(self, sim_time):
        pass
