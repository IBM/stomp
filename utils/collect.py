#!/usr/bin/env python3
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

# DESCRIPTION:
#  This script is used to kick off a run of a large number of tests.
#  It is derived from run_all.py but adds another search dimension --
#  the scaling of the mean task arrival time (ARRIVE_SCALE).
#  This script also supports the output of the results in a "CSV"
#   format, automatically converting the outputs to be comma-separated
#   and to be written into files ending in .csv
#

from __future__ import print_function
import os
import subprocess
import json
import time
import sys
import getopt
from sys import stdout
from subprocess import check_output
from collections import defaultdict
from builtins import str

#Flags to collect additional metrics
extra_waittime = False
extra_util = True
extra_profile = False

# TODO this should be added to the json file
static_power = {
    'cpu_core': 424.2,
    'gpu': 76.9, 
    'tra_accel': 0.1*22.,
    'det_accel': 0.1*28.,
    'loc_accel': 0.1*590.,
    'fft_accel': 0.1*1273,
}

area_mm2 = {
    'cpu_core': 3.9, #(15.85mm2 per quad core)
    'gpu': 55.5, #(3.5*quad core cpu) 
    'tra_accel': 1.15, #12mm2 scaled from 65 to 20 -- Eyeriss
    'det_accel': 1.15, #12mm2 scaled from 65 to 20 -- Eyeriss
    'loc_accel': 1.28, #6539.9um2 scaled from 45 to 20 -- lin)
    'fft_accel': 1.15, #12mm2 scaled from 65 to 20 -- Eyeriss
}

def main(argv):

    # Pass directory to collect metrics on
    sim_dir = argv[1].strip('/')
    
    # Pass aplication run in the directory
    app = argv[2]

    # Choose json file base on application
    if(app == "synthetic"):
        conf_file    = './stomp.json'
    else:
        conf_file    = './stomp2.json'
 
    # Load stomp params from json file
    stomp_params = {}
    with open(conf_file) as conf_file:
        stomp_params = json.load(conf_file)

    # dl_scale to have all applications have the same mean arrival time
    # TODO: Get rid of this by generating traces for all applications at the same mean arrival time
    dl_scale = 1
    if(app == "ad"):
        dl_scale = 5
        mean_arrival_time = 50
    elif(app == "mapping" or app == "package"):
        dl_scale = 2.5
        mean_arrival_time = 25
    elif(app == "synthetic"):
        dl_scale = 1
        mean_arrival_time = 10
    
    # Per policy metrics to collect 
    # TODO: Make this more general: "_1" for priority 1 DAGs and "_2" for priority 2 DAGS
    cnt_1                   = {}
    cnt_dropped_1           = {}
    priority_1_slack        = {}
    priority_1_met          = {}
    priority_1_noaff_per    = {}

    cnt_2                   = {}
    cnt_dropped_2           = {}
    priority_2_slack        = {}
    priority_2_met          = {}
    priority_2_noaff_per    = {}

    cum_resp_time           = {}
    mission_completed       = {}
    total_energy            = {}
    static_energy           = {}
    total_util              = {}
    # TODO: What are these timing metrics? Check meta.py to check their definitions
    ctime                   = {}
    rtime                   = {}
    sranktime               = {}
    dranktime               = {}
    ta_time                 = {}
    to_time                 = {}

    # TODO: What are these metrics? Check meta.py to check their definitions
    wtr_crit                = {}
    lt_wcet_r_crit          = {}
    wtr_crit                = {}
    lt_wcet_r_crit          = {}
    sim_time                = {}

    server_list             = {}
    util_list               = {}

    # define header of output metrics
    header = "ACCEL_COUNT,CPU_COUNT,GPU_COUNT,PWR_MGMT,SLACK_PERC,CONTENTION,DROP,PROB,ARR_SCALE,PTOKS"
    header = header + ",Policy,Cum. response time,Mission time,Mission Completed,Pr1 Met,Pr2 Met,Pr2 Cnt,Dropped Cnt,Energy"
    if (extra_waittime):
        header = header + ",WTR_Nocrit,LTR_NoCrit,WTR_Crit,LTR_Crit,Pr1 Slack,Pr2 Slack,Pr1 aff_pc,Pr2 aff_pc"
    if (extra_profile):
        header = header + ",C time,R time,SRANK time, DRANK time, TA time,TO time"
    if(extra_util):
        header = header + ",Static Energy,accel_util,cpu_util,gpu_util,total_util"
    # Flag to print header
    header_printed = False

    # Collect metric for all runs
    for filename in sorted(os.listdir(sim_dir)):
        if filename.startswith("run_stdout"):
            # File with DAG metrics from meta starts with run_stdout_<basename>.out
            fname_out = str(sim_dir) + '/' + filename

            #Get basename which has info of parameters used in run_all to get the output
            basename = filename.replace("run_stdout_", '')
            basename = basename.replace(".out", '')
            
            # File with HW and task metrics from stomp.py starts with out_<basename>
            fname_util = str(sim_dir) + '/out_' + basename

            # Make sure both files exist
            assert(os.path.exists(fname_out) and os.path.exists(fname_util), "Both DAG and Task output files should be present")
           
            #Retrieve run parameters from basename
            policy, base_split = basename.split("_pwr_mgmt_")
            pwr_mgmt, base_split = base_split.split("_slack_perc_")
            slack_perc, base_split = base_split.split("_cont_")
            cont, base_split = base_split.split("_drop_")
            drop, base_split = base_split.split("_arr_")
            arr_scale, base_split = base_split.split("_prob_")
            prob, base_split = base_split.split("_ptoks_")
            ptoks, base_split = base_split.split("_cpu_")
            cpu_count, base_split = base_split.split("_gpu_")
            gpu_count, accel_count = base_split.split("_accel_")
            #print(policy, pwr_mgmt, slack_perc, cont, drop, arr_scale, prob, ptoks, cpu_count, gpu_count, accel_count)

            # Just to double check make sure slack perc is 0 and ptoks is this large number
            if (pwr_mgmt == False):
                assert(slack_perc == 0 and ptoks == 1000000)

            # Normalize arr_scale for mean_arrival_time
            arr_scale = float(arr_scale) / dl_scale

            #Initialize metrics
            priority_1_slack[policy]        = 0
            priority_1_met[policy]          = 0
            cnt_1[policy]                   = 0
            priority_2_slack[policy]        = 0
            priority_2_met[policy]          = 0
            cnt_2[policy]                   = 0
            cnt_dropped_1[policy]           = 0
            cnt_dropped_2[policy]           = 0
            priority_1_noaff_per[policy]    = 0
            priority_2_noaff_per[policy]    = 0

            cum_resp_time[policy]           = 0
            mission_completed[policy]       = 0
            mission_failed                  = 0
            total_energy[policy]            = 0
            static_energy[policy]           = 0
            total_util[policy]              = 0

            ctime[policy]                   = 0
            rtime[policy]                   = 0
            sranktime[policy]               = 0
            dranktime[policy]               = 0
            ta_time[policy]                 = 0
            to_time[policy]                 = 0

            wtr_crit[policy]                = 0
            lt_wcet_r_crit[policy]          = 0
            wtr_crit[policy]                = 0
            lt_wcet_r_crit[policy]          = 0
            sim_time[policy]                = 0

            server_list[policy]             = ''
            util_list[policy]               = ''

            #Flag to detect header, read DAG data and then the additional metrics
            flag = 0
            with open(fname_out,'r') as fp:
                while(1):
                    line = fp.readline()
                    if not line:
                        break
                    if (line == "Dropped,DAG ID,DAG Priority,DAG Type,Slack,Response Time,No-Affinity Time\n"):
                        # print("Found line")
                        flag = 1
                        continue
                    
                    # Read profiled timing metrics and wait time metrics, sim_time and energy
                    if (line.startswith("Time")):
                        flag = 0
                        #Time: C, R, TA, TO
                        theader,data = line.split(':')
                        #print(data)
                        ct, rt, srank_t, drank_t, ta_t, to_t = data.split(',')

                        ctime[policy]       = float(ct)
                        rtime[policy]       = float(rt)
                        sranktime[policy]   = float(srank_t)
                        dranktime[policy]   = float(drank_t)
                        ta_time[policy]     = float(ta_t)
                        to_time[policy]     = float(to_t)
                        #print(ctime[policy],rtime[policy],ta_time[policy],to_time[policy])

                        line = fp.readline()
                        line = line.strip('\n')
                        wtr_crit[policy], lt_wcet_r_crit[policy], wtr_crit[policy],lt_wcet_r_crit[policy],sim_time[policy],total_energy[policy] = line.split(',')
                        total_energy[policy] = int(total_energy[policy])

                    # Parse per dag metrics
                    if (flag):
                        # TODO: Maybe don't need this condition; Change if not using 1000 DAG traces change
                        if(cnt_1[policy] + cnt_2[policy] >= 1000):
                            break
                        line = line.strip()

                        # Read per dag information
                        dropped,dag_id,priority,dag_type,slack,resp,noafftime = line.split(',')
                        if priority == '1':
                            cnt_1[policy] += 1
                            if (int(dropped) == 1):
                                cnt_dropped_1[policy] += 1
                            else:
                                deadline = stomp_params['simulation']['applications'][app]['dag_types'][dag_type]['deadline'] * (arr_scale * dl_scale)
                                priority_1_slack[policy] += float(slack)/deadline

                                if(float(slack) >= 0):
                                    priority_1_met[policy] += 1
                                priority_1_noaff_per[policy] += float(noafftime)/float(resp)
                        else:
                            cnt_2[policy] += 1
                            if (int(dropped) == 1):
                                cnt_dropped_2[policy] += 1
                            else:
                                deadline = stomp_params['simulation']['applications'][app]['dag_types'][dag_type]['deadline'] * (arr_scale * dl_scale)
                                priority_2_slack[policy] += float(slack)/deadline
                                # If slack of Priority 2 DAGs are negative => Mission has failed
                                if(float(slack) >= 0):
                                    priority_2_met[policy] += 1
                                elif(mission_failed != 1):
                                    mission_failed = 1
                                    mission_completed[policy] = priority_2_met[policy]
                                priority_2_noaff_per[policy] += float(noafftime)/float(resp)
                                cum_resp_time[policy] += float(resp)
            
            server_count = 0
            found = 0
            
            # Populate utilization metrics
            if(extra_util):
                with open(fname_util,'r') as fp:
                    while(1):
                        line = fp.readline()
                        if not line:
                            break

                        if (line == " Busy time and Utilization:\n"):
                            # print("Found line")
                            found = 1
                            line = fp.readline() # Skip next line
                            continue

                        if(found):
                            if (line == "\n"): # Break on empty line
                                break
                            
                            server_count += 1
                            line = line.strip('\n')
                            
                            data1, data2, data3, server, data5, data6, util = line.split()
                            #Get per server utilization
                            server_list[policy] += (server + ',')
                            util_list[policy] += (util + ',')

                header = header + ',' + server_list[policy]

            if(cnt_1[policy] != cnt_dropped_1[policy]):
                priority_1_slack[policy] = float(priority_1_slack[policy])/(cnt_1[policy]-cnt_dropped_1[policy])
                priority_1_noaff_per[policy] = priority_1_noaff_per[policy]/(cnt_1[policy]-cnt_dropped_1[policy])
            priority_2_slack[policy] = float(priority_2_slack[policy])/(cnt_2[policy]-cnt_dropped_2[policy])
            priority_1_met[policy] = float(priority_1_met[policy])/cnt_1[policy]
            priority_2_met[policy] = float(priority_2_met[policy])/cnt_2[policy]


            priority_2_noaff_per[policy] = priority_2_noaff_per[policy]/(cnt_2[policy]-cnt_dropped_2[policy])

            mission_completed[policy] = float(mission_completed[policy])/cnt_2[policy]
            if mission_failed == 0:
                mission_completed[policy] = 1.0;
            if True: #(priority_2_met[policy] == 1): #
                final_accel_count = 0
                accel_util = 0
                final_cpu_count = 0
                cpu_util = 0
                final_gpu_count = 0
                gpu_util = 0
                if(extra_util):
                    servers = server_list[policy].split(',')[:-1]
                    utils = util_list[policy].split(',')[:-1]
                    for x in range(0,len(utils)):
                        if ('accel' in servers[x]): # and float(utils[x]) != 0.):
                            final_accel_count += 1*area_mm2[servers[x]]
                            accel_util += float(utils[x])*area_mm2[servers[x]]
                        if ('cpu' in servers[x]): # and float(utils[x]) != 0.):
                            final_cpu_count += 1*area_mm2[servers[x]]
                            cpu_util += float(utils[x])*area_mm2[servers[x]]
                        if ('gpu' in servers[x]): # and float(utils[x]) != 0.):
                            final_gpu_count += 1*area_mm2[servers[x]]
                            gpu_util += float(utils[x])*area_mm2[servers[x]]

                        static_energy[policy] += ((100. - float(utils[x]))/100)*float(sim_time[policy])*static_power[servers[x]]

                    if (final_accel_count + final_gpu_count + final_cpu_count):
                        total_util[policy] = (accel_util + gpu_util + cpu_util)/ (final_accel_count + final_gpu_count + final_cpu_count)
                    if (final_accel_count):
                        accel_util = accel_util / final_accel_count
                    if(final_gpu_count):
                        gpu_util = gpu_util / final_gpu_count
                    if(final_cpu_count):
                        cpu_util = cpu_util / final_cpu_count
            
                    out = str(accel_count) + "," + \
                        str(cpu_count) + "," + \
                        str(gpu_count) + "," + \
                        str(pwr_mgmt) + "," + \
                        str(slack_perc) + "," + \
                        str(cont) + "," + \
                        str(drop) + "," + \
                        str(prob) + "," + \
                        str(arr_scale) + "," + \
                        str(ptoks) + "," + \
                        str(policy)

                    out += ((",%d,%s,%lf,%lf,%lf,%d,%d,%d") % (cum_resp_time[policy], sim_time[policy], mission_completed[policy], priority_1_met[policy],priority_2_met[policy],cnt_2[policy],cnt_dropped_1[policy],total_energy[policy]))
                    if(extra_waittime):
                        out += ((",%s,%s,%s,%s,%lf,%lf,%lf,%lf") % (wtr_crit[policy],lt_wcet_r_crit[policy], wtr_crit[policy],lt_wcet_r_crit[policy],priority_1_slack[policy],priority_2_slack[policy],priority_1_noaff_per[policy],priority_2_noaff_per[policy]))
                    if(extra_profile):
                        out += ((",%lf,%lf,%lf,%lf,%lf,%lf") % (ctime[policy],rtime[policy],sranktime[policy],dranktime[policy],ta_time[policy],to_time[policy]))
                    
                    if(extra_util):
                        out += ',' + str(static_energy[policy]) + ',' + str(accel_util) + ',' + str(cpu_util) + ',' + str(gpu_util) + ',' + str(total_util[policy]) + ',' +  util_list[policy]

                if(not header_printed):
                    print(header)
                    header_printed = True
                print(out)
                    # break




if __name__ == "__main__":
    assert len(sys.argv) >= 2, "Insufficient args"
    main(sys.argv)
