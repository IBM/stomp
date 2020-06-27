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

from run_all_2 import POLICY, STDEV_FACTOR, ARRIVE_SCALE, PROB, DROP

extra = False
#POLICY       = ['ms1', 'ms2', 'ms3', 'simple_policy_ver2']
# POLICY       = ['ms1', 'ms2', 'ms3', 'simple_policy_ver2', 'simple_policy_ver5', 'edf', 'edf_ver5', 'ms1_update2', 'ms2_update2', 'ms3_update2'] # This is default
# ARRIVE_SCALE = [0.1, 0.2, 0.4, 0.6, 0.8, 1.0, 1.2, 1.4, 1.6, 1.8, 2.0, 2.2]
# PROB         = [0.5, 0.3, 0.2, 0.1]
# DROP         = [True, False]
# STDEV_FACTOR = [0.01]





conf_file    = './stomp.json'

stomp_params = {}
with open(conf_file) as conf_file:
    stomp_params = json.load(conf_file)

mean_arrival_time = stomp_params['simulation']['mean_arrival_time']


deadline_5 = 537
deadline_7 = 428
deadline_10 = 1012
stdev_factor = STDEV_FACTOR[0]

def main(argv):
    sim_dir = argv
    first = 1
    for drop in DROP:
        for prob in PROB:
            for arr_scale in ARRIVE_SCALE:
                for accel_count in range(5,6):
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
                    mission_completed       = {}
                    total_energy            = {}
                    ctime                   = {}
                    rtime                   = {}
                    ta_time                 = {}
                    to_time                 = {}

                    header1 = "ACCEL_COUNT,DROP,PROB,ARR_SCALE"
                    out1 = str(accel_count) + "," + str(drop) + "," + str(prob) + "," + str(arr_scale)
                    for policy in POLICY:
                        header = header1 + ",Policy,Mission time,Mission Completed,Pr1 Met,Pr2 Met,Pr2 Cnt,Energy"
                        if (extra):
                            header = header + "," + policy + " C time,"+ policy + " R time,"+ policy + " TA time,"+ policy + " TO time,"+ policy + " Pr1 Slack," + policy + " Pr2 Slack," + policy + " Pr1 aff_pc," + policy + " Pr2 aff_pc"
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
                        mission_completed[policy]       = 0
                        mission_failed                  = 0
                        total_energy[policy]            = 0

                        ctime[policy]                   = 0
                        rtime[policy]                   = 0
                        ta_time[policy]                 = 0
                        to_time[policy]                 = 0

                        flag = 0
                        # print((str(sim_dir) + '/run_stdout_' + policy + "_arr_" + str(arr_scale) + '_stdvf_' + str(stdev_factor) + '.out'))
                        # with open(str(sim_dir) + '/run_stdout_' + policy + "_arr_" + str(arr_scale) + '_stdvf_' + str(stdev_factor)  + '_cpu_' + str(accel_count) + '.out','r') as fp:
                        #fname = str(sim_dir) + '/run_stdout_' + policy + "_arr_" + str(arr_scale) + '_stdvf_' + str(stdev_factor) + '.out'
                        fname = str(sim_dir) + '/run_stdout_' + policy + "_drop_" + str(drop) + "_arr_" + str(arr_scale) + '_prob_' + str(prob) + '.out'
                        if os.path.exists(fname):
                            pass
                        else:

                            out2 = str(accel_count) + "," + str(drop) + "," + str(prob) + "," + str(arr_scale) + "," + str(policy)
                            print(out2 + ",NodataYet")
                            continue
                        with open(fname,'r') as fp:
                            line = fp.readline()
                            while(line):
                                line = fp.readline()
                                if not line:
                                    break
                                if (line == "Dropped,DAG ID,DAG Priority,DAG Type,Slack,Response Time,No-Affinity Time,Energy\n"):
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


                                if (flag):
                                    if(cnt_1[policy] + cnt_2[policy] >= 1000):
                                        break
                                    # print(line)
                                    dropped,tid,priority,dag_type,slack,resp,noafftime,energy = line.split(',')
                                    total_energy[policy] = int(energy)
                                    if priority == '1':
                                        cnt_1[policy] += 1
                                        if (int(dropped) == 1):
                                            cnt_dropped_1[policy] += 1
                                        else:
                                            if dag_type == '5':
                                                priority_1_slack[policy] += float(slack)/deadline_5
                                            else:
                                                if dag_type == '7':
                                                    priority_1_slack[policy] += float(slack)/deadline_7
                                                else:
                                                    priority_1_slack[policy] += float(slack)/deadline_10
                                            if(float(slack) >= 0):
                                                priority_1_met[policy] += 1
                                            priority_1_noaff_per[policy] += float(noafftime)/float(resp)
                                    else:
                                        cnt_2[policy] += 1
                                        if (int(dropped) == 1):
                                            cnt_dropped_2[policy] += 1
                                        else:
                                            if dag_type == '5':
                                                priority_2_slack[policy] += float(slack)/deadline_5
                                            else:
                                                if dag_type == '7':
                                                    priority_2_slack[policy] += float(slack)/deadline_7
                                                else:
                                                    priority_2_slack[policy] += float(slack)/deadline_10
                                            if(float(slack) >= 0):
                                                priority_2_met[policy] += 1
                                            elif(mission_failed != 1):
                                                mission_failed = 1
                                                mission_completed[policy] = priority_2_met[policy]
                                            priority_2_noaff_per[policy] += float(noafftime)/float(resp)
                                            mission_time[policy] += float(resp)

                        if(cnt_1[policy] != cnt_dropped_1[policy]):
                            priority_1_slack[policy] = float(priority_1_slack[policy])/(cnt_1[policy]-cnt_dropped_1[policy])
                            priority_1_noaff_per[policy] = priority_1_noaff_per[policy]/(cnt_1[policy]-cnt_dropped_1[policy])
                        priority_2_slack[policy] = float(priority_2_slack[policy])/(cnt_2[policy]-cnt_dropped_2[policy])
                        priority_1_met[policy] = float(priority_1_met[policy])/cnt_1[policy]
                        priority_2_met[policy] = float(priority_2_met[policy])/cnt_2[policy]


                        priority_2_noaff_per[policy] = priority_2_noaff_per[policy]/(cnt_2[policy]-cnt_dropped_2[policy])

                        mission_time[policy] += arr_scale*mean_arrival_time*1000
                        mission_completed[policy] = float(mission_completed[policy])/cnt_2[policy]
                        if mission_failed == 0:
                            mission_completed[policy] = 1.0;

                        out = str(accel_count) + "," + str(drop) + "," + str(prob) + "," + str(arr_scale) + "," + str(policy)
                        out += ((",%lf,%lf,%lf,%lf,%d,%d") % (mission_time[policy], mission_completed[policy], priority_1_met[policy],priority_2_met[policy],cnt_2[policy],total_energy[policy]))
                        if(extra):
                            out += ((",%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf") % (ctime[policy],rtime[policy],ta_time[policy],to_time[policy],priority_1_slack[policy],priority_2_slack[policy],priority_1_noaff_per[policy],priority_2_noaff_per[policy]))

                        if(first):
                            print(header)
                            first = 0
                        print(out)
                    #print(out)




if __name__ == "__main__":
    assert len(sys.argv) >= 2, "Insufficient args"
    main(sys.argv[1])
