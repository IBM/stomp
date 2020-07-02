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


# MS3 Update 2 + power constraints + DVFS + reserving task for originally selected server overriding power constraints

from stomp import BaseSchedulingPolicy
import logging
import numpy
from datetime import datetime, timedelta

max_task_depth_to_check = 10

def clamp(x, thres):
    if x < thres:
        return thres
    else:
        return x

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

        # TODO: these should probably go into stomp.py.
        self.total_ptoks  = stomp_params['simulation']['total_ptoks']
        self.avail_ptoks  = self.total_ptoks
        # Percentage of slack to consume for DVFS.
        self.slack_perc   = stomp_params["simulation"]["slack_perc"]
        self.dvfs         = stomp_params["simulation"]["dvfs"]

        self.base_clk     = stomp_params["simulation"]["base_clk"]
        self.v_nom        = stomp_params["simulation"]["v_nom"]
        self.v_th         = stomp_params["simulation"]["v_th"]
        self.power_scale  = stomp_params["simulation"]["power_scale"]

    # Return scaled number of power tokens.
    def get_scaled_power(self, ptoks, clk):
        assert clk > 0.

        v_new = self.v_th / (1 - ((clk / 1.) ** 0.5) * (1 - self.v_th / self.v_nom))
        # Clamp to within 10% of Vth. TODO: parameterize.
        clamp(v_new, self.v_th * 1.1)
        # print("v_th = %f, v_nom = %f, v_new = %f, clk_new = %f, clk_orig = %f" \
        #     " power_scale = %f" % (self.v_th, self.v_nom, v_new, clk, 1, self.power_scale))
        return ptoks * (v_new / self.v_nom) ** self.power_scale

    def apply_dvfs(self, sim_time, task, mean_service_time, ptoks):
        # Scale service time based on
        # - available slack
        # - % of slack to convert to power savings
        clk_scale = 1.
        orig_service_time = mean_service_time
        slack = task.calc_slack(sim_time, orig_service_time)
        usable_slack = slack * self.slack_perc / 100.
        if usable_slack > 0:
            mean_service_time = round(usable_slack + orig_service_time)
            # print("orig_service_time = %u, slack = %u, scaled_service_time = %u" %
            #     (orig_service_time, slack, mean_service_time))
            clk_scale = orig_service_time / mean_service_time
            new_clk = self.base_clk * clk_scale
            orig_rqstd_ptoks = ptoks
            ptoks = self.get_scaled_power(orig_rqstd_ptoks, new_clk)

            # Update service time
            # task.task_service_time = mean_service_time
            # assert window[0].task_service_time == head_task.task_service_time
            # print("orig_rqstd_ptoks = %u, scaled_rqstd_ptoks = %u" % (orig_rqstd_ptoks,
            #     ptoks))
        return mean_service_time, ptoks, clk_scale

    def assign_task_to_server(self, sim_time, tasks, dags_dropped):

        if (len(tasks) == 0):
            # There aren't tasks to serve
            return None

        for task in tasks:
            if task.dag_id in dags_dropped:
                # print("Removing dropped dag")
                tasks.remove(task)

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
                if (server.type in t.mean_service_time_dict):
                    mean_service_time   = t.mean_service_time_dict[server.type]
                    if(max_time < float(mean_service_time)):
                        max_time = float(mean_service_time)
                    if(min_time > float(mean_service_time)):
                        min_time = float(mean_service_time)
                    num_servers += 1


            if ((t.deadline -(sim_time-t.arrival_time) - (max_time)) < 0):
                if(t.priority > 1):
                    slack = 1 - 0.99/((sim_time-t.arrival_time) + max_time - t.deadline)
                    t.rank = int((100000 * (10*t.priority))/slack)
                else:
                    if((t.deadline -(sim_time-t.arrival_time) - (min_time)) >= 0):
                        slack = 1 + (t.deadline - (sim_time-t.arrival_time) - (min_time))
                        t.rank = int((100000 * (t.priority))/slack)
                    else:
                        t.rank = 0
            else:
                slack = 1 + (t.deadline - (sim_time-t.arrival_time) - (max_time))
                t.rank = int((100000 * (10*t.priority))/slack)

            # logging.info("%d: [READY QUEUE TASKS] [%d.%d]" %(sim_time, t.dag_id, t.tid))

        tasks.sort(key=lambda task: task.rank, reverse=True)
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

            if task.reserved_server_id == None:
                # Compute execution times for each target server, factoring in
                # the remaining execution time of tasks already running.
                target_servers = []
                for server in self.servers:

                    # logging.debug('[%10ld] Checking server %s' % (sim_time, server.type))
                    if (server.type in task.mean_service_time_dict):

                        mean_service_time = task.mean_service_time_dict[server.type]
                        if self.dvfs:
                            mean_service_time, ptoks, clk_scale = self.apply_dvfs(
                                sim_time, task, mean_service_time, task.power_dict[server.type])

                        if (server.busy):
                            remaining_time  = server.curr_job_end_time - sim_time
                            for stask in window:
                                if(stask == task):
                                    break
                                if (self.servers.index(server) == stask.possible_server_idx):
                                    assert stask.possible_mean_service_time != None
                                    # print("[%10u][%u.%u] stask[%u.%u] reserved for server %u; mean_service_time = %u (dict=%u)" %
                                    #     (sim_time, task.dag_id, task.tid, stask.dag_id, stask.tid, stask.possible_server_idx,
                                    #         stask.possible_mean_service_time, stask.mean_service_time_dict[server.type]))
                                    remaining_time += stask.possible_mean_service_time # set when server for stask is reserved
                                    # assert stask.possible_mean_service_time == stask.mean_service_time_dict[server.type]
                        else:
                            remaining_time  = 0
                        actual_service_time = mean_service_time + remaining_time

                        logging.debug('[%10ld] Server %s : mst %d ast %d ' %
                            (sim_time, server.type, mean_service_time, actual_service_time))
                        target_servers.append(actual_service_time)
                    else:
                        target_servers.append(float("inf"))

                # Look for the server with smaller actual_service_time
                # and check if it's available
                server_idx = target_servers.index(min(target_servers))
            else:
                server_idx = task.reserved_server_id

            server = self.servers[server_idx]

            rqstd_ptoks = task.power_dict[server.type]
            mean_service_time = task.mean_service_time_dict[server.type]
            # print("[%10u][%u.%u] mean_service_time_dict[Server %u] = %u" %
            #     (sim_time, task.dag_id, task.tid, server_idx, task.mean_service_time_dict[server.type]))

            if not server.busy:           # Server is not busy.
                if self.dvfs:
                    mean_service_time, rqstd_ptoks, clk_scale = self.apply_dvfs(
                        sim_time, task, mean_service_time, rqstd_ptoks)
                else:
                    clk_scale = 1.

                if rqstd_ptoks <= self.avail_ptoks:         # Have sufficient power tokens.
                    if not server.reserved or \
                        task.reserved_server_id == server_idx:   # Server is not reserved OR reserved for this task.
                        # Clear reserved bit and invalidate reserved_for_task.
                        server.reserved = False

                        # Pop task in queue's head and assign it to server
                        # ttask = window.pop(tidx);
                        # tasks.remove(ttask)
                        # print("TASK %u.%u" % (task.dag_id, task.tid))
                        tasks.remove(task)
                        task.ptoks_used = rqstd_ptoks
                        # print("TASK %u.%u" % (task.dag_id, task.tid))

                        # logging.debug('[%10ld] Scheduling task %2d %s to server %2d %s' % (sim_time, tidx, ttask.type, server_idx, self.servers[server_idx].type))

                        # Embed the actual ptoks used by task into its object
                        server.assign_task(sim_time, task, 1 / clk_scale)
                        self.avail_ptoks -= task.ptoks_used
                        # if sim_time >= 12000:
                        # logging.info("[%10u] [%u.%u] rqstd_ptoks = %d, avail_ptoks now is = %d, server assigned: %d" %
                        #     (sim_time, task.dag_id, task.tid, task.ptoks_used, self.avail_ptoks, server.id))
                        bin = int(tidx / self.bin_size)
                        if (bin >= len(self.stats['Task Issue Posn'])):
                            bin = len(self.stats['Task Issue Posn']) - 1
                        # logging.debug('[          ] Set BIN from %d / %d to %d vs %d = %d' % (tidx, self.bin_size, int(tidx / self.bin_size), len(self.stats['Task Issue Posn']), bin))
                        self.stats['Task Issue Posn'][bin] += 1
                        end = datetime.now()
                        self.ta_time += end - start
                        # print(("TA: %d")%(self.ta_time.microseconds))
                        return server
                    else:
                        pass
                        # print("[%10u] Else case: [%u.%u] want server: %d" % (sim_time, task.dag_id, task.tid, server.id))
                else:   # Not enough tokens, reserve server for later.
                    # if sim_time >= 12000:
                    # logging.info("[%10u] [%u.%u] Stalling because not enough power tokens (rqstd=%u, avail=%u), reserving server: %d" %
                    #     (sim_time, task.dag_id, task.tid, rqstd_ptoks, self.avail_ptoks, server.id))
                    server.reserved                 = True
                    task.reserved_server_id         = server_idx
                    task.possible_server_idx        = server_idx    # Used by other tasks to calculate best finish time
                    task.possible_mean_service_time = mean_service_time
            else:
                # if sim_time >= 12000:
                # logging.info("[%10u][%u.%u] Server %u Busy, assigning to virtual queue; mean_service_time = %u" %
                #     (sim_time, task.dag_id, task.tid, server_idx, mean_service_time))
                task.possible_server_idx        = server_idx
                task.possible_mean_service_time = mean_service_time
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

