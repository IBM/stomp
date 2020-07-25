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

from run_all_2 import POLICY, PWR_MGMT, SLACK_PERC, STDEV_FACTOR, ARRIVE_SCALE0, ARRIVE_SCALE1, ARRIVE_SCALE2, PROB, DROP, PTOKS, POLICY_SOTA

extra = False
extra1 = False
#POLICY       = ['ms1', 'ms2', 'ms3', 'simple_policy_ver2']
# POLICY       = ['ms1', 'ms2', 'ms3', 'simple_policy_ver2', 'simple_policy_ver5', 'edf', 'edf_ver5', 'ms1_update2', 'ms2_update2', 'ms3_update2'] # This is default
# ARRIVE_SCALE = [0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2]
# PROB         = [0.5, 0.3, 0.2, 0.1]
# DROP         = [True, False]
# STDEV_FACTOR = [0.01]

ARRIVE_SCALE = ARRIVE_SCALE0 + ARRIVE_SCALE1 + ARRIVE_SCALE2

stdev_factor = STDEV_FACTOR[0]

def main(argv):
    # DL_5 = 537
    # DL_7 = 428
    # DL_10 = 1012

    sim_dir = argv[1].strip('/')
    app = argv[2]
    ACCEL_COUNT = 1
    if(argv[3] == 'hetero'):
        ACCEL_COUNT = 6
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
                for prob in PROB:

                    for ptoks in PTOKS_:
                        for accel_count in range(0,ACCEL_COUNT):
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
                            ctime                   = {}
                            rtime                   = {}
                            ta_time                 = {}
                            to_time                 = {}

                            wtr_crit                = {}
                            lt_wcet_r_crit          = {}
                            wtr_crit                = {}
                            lt_wcet_r_crit          = {}
                            sim_time                = {}

                            server_list             = {}
                            util_list               = {}

                            header1 = "ACCEL_COUNT,PWR_MGMT,SLACK_PERC,DROP,PROB,ARR_SCALE,PTOKS"
                            # out1 = str(accel_count) + "," + \
                            #     str(pwr_mgmt) + "," + \
                            #     str(slack_perc) + "," + \
                            #     str(drop) + "," + \
                            #     str(prob) + "," + \
                            #     str(arr_scale) + "," + \
                            #     str(ptoks)
                            for policy in POLICY:

                                # if (app != "synthetic"):
                                #     if(app != "ad"):
                                #         if policy in POLICY_SOTA:
                                #             if (policy == "ads"):
                                #                 ARRIVE_SCALE     = [3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5]
                                #             else:
                                #                 ARRIVE_SCALE = [5.0, 5.5, 6.0, 6.5, 7.0, 7.5, 8.0, 8.5, 9.0, 9.5, 10.0, 10.5, 11.0, 11.5]
                                #         else:
                                #             ARRIVE_SCALE     = [0.1, 0.5, 0.7, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
                                #     else:
                                #         ARRIVE_SCALE     = [0.1, 0.5, 0.7, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
                                # else:
                                #     ARRIVE_SCALE     = [0.1, 0.5, 0.7, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]

                                for arr_scale in ARRIVE_SCALE:
                                    # print("dl_scale", dl_scale)

                                    arr_scale = arr_scale / dl_scale
                                    # deadline_5 = DL_5 * (arr_scale * stomp_params['simulation']['deadline_scale'])
                                    # deadline_7 = DL_7 * (arr_scale * stomp_params['simulation']['deadline_scale'])
                                    # deadline_10 = DL_10 * (arr_scale * stomp_params['simulation']['deadline_scale'])
                                    # print(deadline_5, deadline_7, deadline_10)


                                    header = header1 + ",Policy,Mission time,Mission time1,Mission time2,Mission Completed,Pr1 Met,Pr2 Met,Pr2 Cnt,Dropped Cnt,Energy"
                                    if (extra):
                                        header = header + ",WTR_Nocrit,LTR_NoCrit,WTR_Crit,LTR_Crit,C time,R time,TA time,TO time,Pr1 Slack,Pr2 Slack,Pr1 aff_pc,Pr2 aff_pc"
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

                                    ctime[policy]                   = 0
                                    rtime[policy]                   = 0
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
                                    basename = policy + \
                                        "_pwr_mgmt_" + str(pwr_mgmt) + \
                                        "_slack_perc_" + str(slack_perc) + \
                                        "_drop_" + str(drop) + \
                                        "_arr_" + str(arr_scale) + \
                                        '_prob_' + str(prob) + \
                                        '_ptoks_' + str(ptoks) + \
                                        '_accel_' + str(accel_count)
                                    fname_out = str(sim_dir) + '/run_stdout_' + basename + '.out'
                                    fname_util = str(sim_dir) + '/out_' + basename
                                    # print(fname_out)
                                    if os.path.exists(fname_out):
                                        pass

                                    else:

                                        out2 = str(accel_count) + "," + \
                                            str(pwr_mgmt) + "," + \
                                            str(slack_perc) + "," + \
                                            str(drop) + "," + \
                                            str(prob) + "," + \
                                            str(arr_scale) + "," + \
                                            str(ptoks) + "," + \
                                            str(policy)
                                        print(out2 + ",NodataYet")
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
                                                ct, rt, ta_t, to_t = data.split(',')

                                                ctime[policy]       = float(ct)
                                                rtime[policy]       = float(rt)
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

                                    if(extra1):
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
                                        

                                        # print(server_list[policy])

                                        header += ',' + server_list[policy]
                                    # print(util_list[policy])



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

                                    out = str(accel_count) + "," + \
                                        str(pwr_mgmt) + "," + \
                                        str(slack_perc) + "," + \
                                        str(drop) + "," + \
                                        str(prob) + "," + \
                                        str(arr_scale) + "," + \
                                        str(ptoks) + "," + \
                                        str(policy)
                                    out += ((",%d,%d,%s,%lf,%lf,%lf,%d,%d,%d") % (mission_time[policy], mission_time1[policy], sim_time[policy], mission_completed[policy], priority_1_met[policy],priority_2_met[policy],cnt_2[policy],cnt_dropped_1[policy],total_energy[policy]))
                                    if(extra):
                                        out += ((",%s,%s,%s,%s,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf") % (wtr_crit[policy],lt_wcet_r_crit[policy], wtr_crit[policy],lt_wcet_r_crit[policy],ctime[policy],rtime[policy],ta_time[policy],to_time[policy],priority_1_slack[policy],priority_2_slack[policy],priority_1_noaff_per[policy],priority_2_noaff_per[policy]))
                                    if(extra1):
                                        out += ',' + util_list[policy]
                                    if(first):
                                        print(header)
                                        first = 0
                                    print(out)




if __name__ == "__main__":
    assert len(sys.argv) >= 2, "Insufficient args"
    main(sys.argv)
