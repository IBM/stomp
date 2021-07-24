#!/usr/bin/env python2
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
from __builtin__ import str

from run_all_2 import RUNS, DELTA, POLICY, PWR_MGMT, SLACK_PERC, STDEV_FACTOR, ARRIVE_SCALE0, ARRIVE_SCALE1, ARRIVE_SCALE2, ARRIVE_SCALE3, ARRIVE_SCALE4, ARRIVE_SCALE5, PROB, CONTENTION, DROP, PTOKS, POLICY_SOTA

extra = False
extra_util = True
extra_profile = False

ARRIVE_SCALE = ARRIVE_SCALE0 + ARRIVE_SCALE1 + ARRIVE_SCALE2 + ARRIVE_SCALE3 + ARRIVE_SCALE4 + ARRIVE_SCALE5

stdev_factor = STDEV_FACTOR[0]

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
    # DL_5 = 537
    # DL_7 = 428
    # DL_10 = 1012

    sim_dir = argv[1].strip('/')
    app = argv[2]
    ACCEL_COUNT = 1
    if(len(argv) >= 4 and  argv[3] == 'hetero'):
        ACCEL_COUNT = 9
    # app,temp = sim_dir.split('_')
    # app = "mapping"
    # app = "synthetic"
    # print(app)

    if(app == "synthetic"):
        conf_file    = './stomp.json'
    else:
        conf_file    = './stomp2.json'
    
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

    stomp_params = {}
    with open(conf_file) as conf_file:
        stomp_params = json.load(conf_file)

    ARRIVE_SCALE_FINAL = []
    ARRIVE_SCALE_SORT = sorted(list(set(ARRIVE_SCALE)))
    max_val = max(ARRIVE_SCALE_SORT)*1000
    arr_scale1 = min(ARRIVE_SCALE_SORT)*1000
    while arr_scale1 <= max_val + RUNS*DELTA*1000:
        ARRIVE_SCALE_FINAL.append(arr_scale1/1000)
        arr_scale1 += DELTA*1000

    first = 1
    for pwr_mgmt in PWR_MGMT:
        if pwr_mgmt == False:
            SLACK_PERC_ = [0]
            PTOKS_ = [1000000]
        else:
            SLACK_PERC_ = SLACK_PERC
            PTOKS_ = PTOKS
        for slack_perc in SLACK_PERC_:
            for drop in DROP:
                for cont in CONTENTION:
                    for prob in PROB:
                        for ptoks in PTOKS_:
                            for accel_count in [0, 2, 4, 8]:
                                for cpu_count in [2, 4, 8]:
                                    for gpu_count in [0, 2, 4, 8]:
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

                                        mission_time            = {}
                                        mission_time1           = {}
                                        mission_completed       = {}
                                        total_energy            = {}
                                        static_energy           = {}
                                        total_util              = {}
                                        ctime                   = {}
                                        rtime                   = {}
                                        sranktime               = {}
                                        dranktime               = {}
                                        ta_time                 = {}
                                        to_time                 = {}

                                        wtr_crit                = {}
                                        lt_wcet_r_crit          = {}
                                        wtr_crit                = {}
                                        lt_wcet_r_crit          = {}
                                        sim_time                = {}

                                        server_list             = {}
                                        util_list               = {}

                                        header1 = "ACCEL_COUNT,CPU_COUNT,GPU_COUNT,PWR_MGMT,SLACK_PERC,CONTENTION,DROP,PROB,ARR_SCALE,PTOKS"
                                        for policy in POLICY:

                                            count = 0
                                            min_factor = None
                                            min_out = ''
                                            for arr_scale1 in ARRIVE_SCALE_FINAL:
                                                # for y in range(0,RUNS):
                                                arr_scale = arr_scale1 # + y*DELTA

                                                arr_scale = arr_scale / dl_scale

                                                header = header1 + ",Policy,Mission time,Mission time2,Mission Completed,Pr1 Met,Pr2 Met,Pr2 Cnt,Dropped Cnt,Energy"
                                                if (extra):
                                                    header = header + ",WTR_Nocrit,LTR_NoCrit,WTR_Crit,LTR_Crit,Pr1 Slack,Pr2 Slack,Pr1 aff_pc,Pr2 aff_pc"
                                                if (extra_profile):
                                                    header = header + ",C time,R time,SRANK time, DRANK time, TA time,TO time"
                                                if(extra_util):
                                                    header = header + ",Static Energy,accel_util,cpu_util,gpu_util,total_util"

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
                                                mission_time[policy]            = 0
                                                mission_time1[policy]           = 0
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

                                                flag = 0
                                                # print((str(sim_dir) + '/run_stdout_' + policy + "_arr_" + str(arr_scale) + '_stdvf_' + str(stdev_factor) + '.out'))
                                                # with open(str(sim_dir) + '/run_stdout_' + policy + "_arr_" + str(arr_scale) + '_stdvf_' + str(stdev_factor)  + '_cpu_' + str(accel_count) + '.out','r') as fp:
                                                #fname_out = str(sim_dir) + '/run_stdout_' + policy + "_arr_" + str(arr_scale) + '_stdvf_' + str(stdev_factor) + '.out'
                                                if arr_scale % 1 == 0:
                                                    arr_scale = int(arr_scale)

                                                basename = policy + \
                                                    "_pwr_mgmt_" + str(pwr_mgmt) + \
                                                    "_slack_perc_" + str(slack_perc) + \
                                                    "_cont_" + str(cont) + \
                                                    "_drop_" + str(drop) + \
                                                    "_arr_" + str(arr_scale) + \
                                                    '_prob_' + str(prob) + \
                                                    '_ptoks_' + str(ptoks) + \
                                                    '_cpu_' + str(cpu_count) + \
                                                    '_gpu_' + str(gpu_count) + \
                                                    '_accel_' + str(accel_count)
                                                fname_out = str(sim_dir) + '/run_stdout_' + basename + '.out'
                                                fname_util = str(sim_dir) + '/out_' + basename
                                                if os.path.exists(fname_out) and os.path.exists(fname_util):
                                                    pass
                                                else:
                                                    # print(fname_out)
                                                    # out2 = str(accel_count) + "," + \
                                                    #     str(cpu_count) + "," + \
                                                    #     str(gpu_count) + "," + \
                                                    #     str(pwr_mgmt) + "," + \
                                                    #     str(slack_perc) + "," + \
                                                    #     str(cont) + "," + \
                                                    #     str(drop) + "," + \
                                                    #     str(prob) + "," + \
                                                    #     str(arr_scale) + "," + \
                                                    #     str(ptoks) + "," + \
                                                    #     str(policy)
                                                    # print(out2 + ",NodataYet")
                                                    continue
                                                with open(fname_out,'r') as fp:
                                                    while(1):
                                                        line = fp.readline()
                                                        if not line:
                                                            break
                                                        if (line == "Dropped,DAG ID,DAG Priority,DAG Type,Slack,Response Time,No-Affinity Time\n"):
                                                            # print("Found line")
                                                            flag = 1
                                                            continue

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


                                                        if (flag):
                                                            if(cnt_1[policy] + cnt_2[policy] >= 1000):
                                                                break
                                                            # print(line)
                                                            line = line.strip()
                                                            # dropped,tid,priority,dag_type,slack,resp,noafftime,energy = line.split(',')
                                                            dropped,tid,priority,dag_type,slack,resp,noafftime = line.split(',')

                                                            # total_energy[policy] = float(energy)
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
                                                                    print("Dropped", tid)
                                                                else:
                                                                    deadline = stomp_params['simulation']['applications'][app]['dag_types'][dag_type]['deadline'] * (arr_scale * dl_scale)
                                                                    priority_2_slack[policy] += float(slack)/deadline
                                                                    # print(dag_type, slack, deadline)

                                                                    if(float(slack) >= 0):
                                                                        priority_2_met[policy] += 1
                                                                    elif(mission_failed != 1):
                                                                        mission_failed = 1
                                                                        mission_completed[policy] = priority_2_met[policy]
                                                                    priority_2_noaff_per[policy] += float(noafftime)/float(resp)
                                                                    # print(mission_time)
                                                                    mission_time[policy] += float(resp)
                                                                    mission_time1[policy] += deadline
                                                                    # print(resp, deadline)
                                                
                                                server_count = 0
                                                found = 0

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
                                                                    # print("Break here")
                                                                    break
                                                                
                                                                server_count += 1
                                                                line = line.strip('\n')
                                                                
                                                                # print(line)
                                                                data1, data2, data3, server, data5, data6, util = line.split()
                                                                # print(line.split())
                                                                server_list[policy] += (server + ',')
                                                                util_list[policy] += (util + ',')
                                                                # print(server, util)

                                                    header = header + ',' + server_list[policy]

                                                if(cnt_1[policy] != cnt_dropped_1[policy]):
                                                    priority_1_slack[policy] = float(priority_1_slack[policy])/(cnt_1[policy]-cnt_dropped_1[policy])
                                                    priority_1_noaff_per[policy] = priority_1_noaff_per[policy]/(cnt_1[policy]-cnt_dropped_1[policy])
                                                priority_2_slack[policy] = float(priority_2_slack[policy])/(cnt_2[policy]-cnt_dropped_2[policy])
                                                priority_1_met[policy] = float(priority_1_met[policy])/cnt_1[policy]
                                                priority_2_met[policy] = float(priority_2_met[policy])/cnt_2[policy]


                                                priority_2_noaff_per[policy] = priority_2_noaff_per[policy]/(cnt_2[policy]-cnt_dropped_2[policy])
                                                # print(mission_time)

                                                mission_time[policy] += arr_scale*mean_arrival_time*1000
                                                mission_time1[policy] += arr_scale*mean_arrival_time*1000
                                                # print("Adding", arr_scale, arr_scale*mean_arrival_time*1000)
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
                                                    # total_util[policy] = 0
                                                    if(extra_util):
                                                        # print(arr_scale, server_list[policy])
                                                        servers = server_list[policy].split(',')[:-1]
                                                        utils = util_list[policy].split(',')[:-1]
                                                        # print(utils)
                                                        # print(servers)
                                                        for x in xrange(0,len(utils)):
                                                            if ('accel' in servers[x]): # and float(utils[x]) != 0.):
                                                                # print(servers[x], utils[x])
                                                                final_accel_count += 1*area_mm2[servers[x]]
                                                                accel_util += float(utils[x])*area_mm2[servers[x]]
                                                            if ('cpu' in servers[x]): # and float(utils[x]) != 0.):
                                                                # print(servers[x], utils[x])
                                                                final_cpu_count += 1*area_mm2[servers[x]]
                                                                cpu_util += float(utils[x])*area_mm2[servers[x]]
                                                            if ('gpu' in servers[x]): # and float(utils[x]) != 0.):
                                                                # print(servers[x], utils[x])
                                                                final_gpu_count += 1*area_mm2[servers[x]]
                                                                gpu_util += float(utils[x])*area_mm2[servers[x]]

                                                            
                                                            # print(sim_time[policy])
                                                            # print(servers[x])
                                                            # print(static_power[servers[x]])
                                                            # print(float(utils[x]))
                                                            static_energy[policy] += ((100. - float(utils[x]))/100)*float(sim_time[policy])*static_power[servers[x]]

                                                        if (final_accel_count + final_gpu_count + final_cpu_count):
                                                            total_util[policy] = (accel_util + gpu_util + cpu_util)/ (final_accel_count + final_gpu_count + final_cpu_count)
                                                        if (final_accel_count):
                                                            accel_util = accel_util / final_accel_count
                                                        if(final_gpu_count):
                                                            gpu_util = gpu_util / final_gpu_count
                                                        if(final_cpu_count):
                                                            cpu_util = cpu_util / final_cpu_count
                                                
                                                    # print(total_util[policy], fname_util)
                                                    factor = float(sim_time[policy]) # * (float(total_energy[policy]) + float(static_energy[policy])) #* (final_accel_count + final_gpu_count + final_cpu_count)/total_util[policy]
                                                    if min_factor == None or (min_factor != None and min_factor > factor):
                                                        # print(fname_out, fname_util, "sim time", min_factor)
                                                        min_factor = factor

                                                        min_header = header
                                                        min_out = str(accel_count) + "," + \
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

                                                        min_out += ((",%d,%s,%lf,%lf,%lf,%d,%d,%d") % (mission_time[policy], sim_time[policy], mission_completed[policy], priority_1_met[policy],priority_2_met[policy],cnt_2[policy],cnt_dropped_1[policy],total_energy[policy]))
                                                        if(extra):
                                                            min_out += ((",%s,%s,%s,%s,%lf,%lf,%lf,%lf") % (wtr_crit[policy],lt_wcet_r_crit[policy], wtr_crit[policy],lt_wcet_r_crit[policy],priority_1_slack[policy],priority_2_slack[policy],priority_1_noaff_per[policy],priority_2_noaff_per[policy]))
                                                        if(extra_profile):
                                                            min_out += ((",%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf") % (ctime[policy],rtime[policy],sranktime[policy],dranktime[policy],ta_time[policy],to_time[policy]))
                                                        
                                                        if(extra_util):
                                                            # print(accel_count, cpu_count, gpu_count,accel_util,cpu_util,gpu_util,servers)
                                                            min_out += ',' + str(static_energy[policy]) + ',' + str(accel_util) + ',' + str(cpu_util) + ',' + str(gpu_util) + ',' + str(total_util[policy]) + ',' +  util_list[policy]

                                                        # count += 1
                                        
                                                # if (priority_2_met[policy] == 1):
                                                #     print("Count: ", accel_count, cpu_count, gpu_count, prob, policy, count)
                                                #     count = 0
                                                #     break
                                            if (min_factor != None):
                                                if(first):
                                                    print(min_header)
                                                    first = 0
                                                print(min_out)
                                                    # break




if __name__ == "__main__":
    assert len(sys.argv) >= 2, "Insufficient args"
    main(sys.argv)
