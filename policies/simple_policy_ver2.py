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
#  queue in its best scheduling option (i.e. fastest server). If the best
#  scheduling option isn't available, the policy will try to schedule the
#  task in less-optimal server platforms.  This policy tries to clear the
#  first task by allowing any (eligible) server to execute it even if it is
#  not the most optimal execution platform.

from stomp import BaseSchedulingPolicy

class SchedulingPolicy(BaseSchedulingPolicy):

    def init(self, servers, stomp_stats, stomp_params):
        
        self.stomp_stats  = stomp_stats
        self.stomp_params = stomp_params
        self.servers      = servers
        self.n_servers    = len(servers)


    def assign_task_to_server(self, sim_time, tasks):

        if (len(tasks) == 0):
            # There aren't tasks to serve
            return None    
        
        # Look for an available server to process the task
        for target_server in tasks[0].mean_service_time_list:
            
            target_server_type = target_server[0]
            
            for server in self.servers:
        
                if (server.type == target_server_type and not server.busy):
    
                    # Pop task in queue's head and assign it to server
                    server.assign_task(sim_time, tasks.pop(0))
                    
                    return server
                
        return None


    def remove_task_from_server(self, sim_time, server):
        pass
