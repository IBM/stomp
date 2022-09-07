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
#  This scheduling policy maps tasks based on a static profile and 
#  uses the Martopt advisor to assign tokens to determine service time

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
        self.pwr_mgmt     = stomp_params['simulation']['pwr_mgmt']
        self.pwr_model    = stomp_params["simulation"]["pwr_model"]
        self.total_ptoks  = stomp_params['simulation']['total_ptoks']
        self.avail_ptoks  = self.total_ptoks
        # Percentage of slack to consume for DVFS.
        self.slack_perc   = stomp_params["simulation"]["slack_perc"]
        self.dvfs         = stomp_params["simulation"]["dvfs"]  # This is hardcoded in stomp.json.

        self.base_clk     = stomp_params["simulation"]["base_clk"]
        self.min_clk_f    = stomp_params["simulation"]["min_clk_f"]
        self.v_nom        = stomp_params["simulation"]["v_nom"]
        self.v_th         = stomp_params["simulation"]["v_th"]
        self.v_min        = stomp_params["simulation"]["v_min"]
        self.power_scale  = stomp_params["simulation"]["power_scale"]

    # Return scaled number of power tokens. Voltage is clamped to v_min if it falls lower than that.
    # Clock is also clamped to the clock at v_min.
    def get_scaled_power_clk(self, ptoks, clk_new):
        assert clk_new > 0.

        if self.pwr_model == "simple":
            v_new = self.v_nom * clk_new / self.base_clk
        else:
            # v_new = self.v_th / (1 - ((clk_new / self.base_clk) ** 0.5) * (1 - self.v_th / self.v_nom))
            assert False, "Unsupported"

        v_new_clamped = clamp(v_new, self.v_min)

        if v_new_clamped > v_new:
            # Recalculate clock for clamped voltage.
            if self.pwr_model == "simple":
                clk_new = self.base_clk * (v_new_clamped / self.v_nom)
            else:
                # clk_new = self.base_clk * ((1 - self.v_th / v_new_clamped) / (1 - self.v_th / self.v_nom)) ** 2
                assert False, "Unsupported"

        v_new = v_new_clamped

        # print("v_th = %f, v_nom = %f, v_new = %f, clk_old = %f, clk_new = %f, clk_new_orig = %f" \
        #     " power_scale = %f" % (self.v_th, self.v_nom, v_new, self.base_clk, clk_new, 1, self.power_scale))
        return int(ptoks * (v_new / self.v_nom) ** self.power_scale), clk_new

    def apply_dvfs(self, sim_time, task, mean_service_time, ptoks):
        # Scale service time based on
        # - available slack
        # - % of slack to convert to power savings
        clk_scale = 1.
        orig_service_time = mean_service_time
        slack = task.calc_slack(sim_time, orig_service_time, 0)
        usable_slack = slack * self.slack_perc / 100.
        # print("slack = %u, usable_slack = %u" % (slack, usable_slack))
        if usable_slack > 0:

            # Assume linear relationship b/w clock and service time.
            clk_scale = orig_service_time / (usable_slack + orig_service_time)
            # Clamp clock to lower bound.
            clk_scale = clamp(clk_scale, self.min_clk_f)

            new_clk = self.base_clk * clk_scale
            orig_rqstd_ptoks = ptoks
            ptoks, new_clk = self.get_scaled_power_clk(orig_rqstd_ptoks, new_clk)
            clk_scale = new_clk / self.base_clk

            # Now scale the service time linearly with clock scale.
            mean_service_time = round(orig_service_time / clk_scale)

            # print("orig_service_time = %u, slack = %u, usable_slack = %u, scaled_service_time = %u" %
            #     (orig_service_time, slack, usable_slack, mean_service_time))

            # print("orig_rqstd_ptoks = %u, scaled_rqstd_ptoks = %u" % (orig_rqstd_ptoks,
            #     ptoks))
            # print("orig_service_time = %u, mean_service_time = %u" % (orig_service_time,
            #     mean_service_time))
        else:
            pass
            # print("no usable slack")
        return mean_service_time, ptoks, clk_scale, slack, usable_slack

    def assign_task_to_server(self, sim_time, tasks, dags_dropped, stomp_obj):

        removable_tasks = []
        for task in tasks:
            if dags_dropped.contains(task.dag_id):
                removable_tasks.append(task)
                if (task.priority > 1):
                    stomp_obj.num_critical_tasks -= 1

        for task in removable_tasks:
            tasks.remove(task)
        removable_tasks = []

        if (len(tasks) == 0):
            # There aren't tasks to serve
            return None

        if (len(tasks) > max_task_depth_to_check):
            window_len = max_task_depth_to_check
        else:
            window_len = len(tasks)

        start = datetime.now()
        end = datetime.now()
        self.to_time += end - start

        window = tasks[:window_len]

        tidx = 0;
        start = datetime.now()
        free_cpu_count = 0
        for server in self.servers:
            if not server.busy and server.type == "cpu_core":
                free_cpu_count += 1

        for task in window:
            # logging.debug('[%10ld] Attempting to schedule task %2d : %s' % (sim_time, tidx, task.type))

            server_idx = task.static_server_id
            print(server_idx)
            server = self.servers[server_idx]

            #Request tokens from LNN Advisor
            rqstd_ptoks = server.martopt.request_tokens() * self.total_ptoks / 100
            mean_service_time = task.mean_service_time_dict[server.type]

            if not server.busy:           # Server is not busy.
                if self.pwr_mgmt and self.dvfs:
                    # logging.info('[%10ld] [%d.%d] Applying dvfs ' % (sim_time, task.dag_id, task.tid))
                    orig_mst = mean_service_time
                    orig_pwr = rqstd_ptoks
                    orig_energy = mean_service_time * rqstd_ptoks
                    mean_service_time, rqstd_ptoks, clk_scale, slack_, usable_slack_ = self.apply_dvfs(
                        sim_time, task, mean_service_time, rqstd_ptoks)
                    new_energy = mean_service_time * rqstd_ptoks
                else:
                    clk_scale = 1.

                if not self.pwr_mgmt or \
                    rqstd_ptoks <= self.avail_ptoks:         # Power management is disabled or have sufficient power tokens.
                    # Pop task in queue and assign it to server
                    tasks.remove(task)
                    if (task.priority > 1):
                        stomp_obj.num_critical_tasks -= 1
                    task.ptoks_used = rqstd_ptoks

                    # Embed the actual ptoks used by task into its object
                    server.assign_task(sim_time, task, 1 / clk_scale)
                    if self.pwr_mgmt:
                        self.avail_ptoks -= task.ptoks_used
                    bin = int(tidx / self.bin_size)
                    if (bin >= len(self.stats['Task Issue Posn'])):
                        bin = len(self.stats['Task Issue Posn']) - 1
                    # logging.debug('[          ] Set BIN from %d / %d to %d vs %d = %d' % (tidx, self.bin_size, int(tidx / self.bin_size), len(self.stats['Task Issue Posn']), bin))
                    self.stats['Task Issue Posn'][bin] += 1
                    end = datetime.now()
                    self.ta_time += end - start
                    return server
                else:   # Not enough tokens, reserve server for later.
                    task.possible_server_idx        = server_idx    # Used by other tasks to calculate best finish time
                    task.possible_mean_service_time = mean_service_time
            else:
                task.possible_server_idx        = server_idx
                task.possible_mean_service_time = mean_service_time
            tidx += 1  # Increment task idx
        end = datetime.now()
        self.ta_time += end - start
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
