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
#  This is effectively a sorted earliest-out-of-queue approach, where the
#  task checks the fastest servers, then the next-fastest servers, etc. until
#  it finds one that is not busy.

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

        self.pwr_mgmt     = stomp_params['simulation']['pwr_mgmt']
        self.total_ptoks  = stomp_params['simulation']['total_ptoks']
        self.avail_ptoks  = self.total_ptoks

    def assign_task_to_server(self, sim_time, tasks, dags_dropped, stomp_obj):
        # print(tasks)
        if (len(tasks) == 0):
            # There aren't tasks to serve
            return None

        for target_server in tasks[0].mean_service_time_list:
            target_server_type = target_server[0]
            rqstd_ptoks = tasks[0].power_dict[target_server_type]

            for server in self.servers:
                if (server.type == target_server_type) and \
                    not server.busy:
                    if self.pwr_mgmt and rqstd_ptoks > self.avail_ptoks:
                        # print("Stalling because not enough power tokens")
                        continue
                    # for target_server1 in tasks[0].mean_service_time_list:
                    #     target_server_type = target_server1[0]
                    #     print(str(target_server_type) + "," + str(tasks[0].per_server_service_dict[target_server_type]))

                    # Pop task in queue's head and assign it to server
                    task = tasks.pop(0)

                    # if task.dag_id == 41 and task.tid == 0:
                    #     print(sim_time, task)

                    task.ptoks_used = task.power_dict[server.type]
                    server.assign_task(sim_time, task)
                    assert server.busy
                    assert server.task != None
                    if self.pwr_mgmt:
                        self.avail_ptoks -= rqstd_ptoks
                    # print("Scheduled to server %s, remaining ptoks = %d/%d"
                    #     % (target_server_type, self.avail_ptoks, self.total_ptoks))
                    return server

        return None


    def remove_task_from_server(self, sim_time, server):
        pass

    def output_final_stats(self, sim_time):
        pass