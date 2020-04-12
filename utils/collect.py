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

from run_all_2 import POLICY, STDEV_FACTOR, ARRIVE_SCALE, PROB


CONF_FILE    = './stomp.json'



deadline_5 = 537
deadline_7 = 428
deadline_10 = 1012
stdev_factor = STDEV_FACTOR[0]

def main(argv):
    sim_dir = argv
    first = 1
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
            ctime                   = {}
            rtime                   = {}
            ta_time                 = {}
            to_time                 = {}

            header = "ACCEL_COUNT,ARR_SCALE,STDEV_FACTOR"
            out = str(accel_count) + "," + str(arr_scale)
            for prob in PROB:
                out += "," + str(stdev_factor) 
                for policy in POLICY:
                    header = header + "," + policy + " Mission time,"+ policy + " C time,"+ policy + " R time,"+ policy + " TA time,"+ policy + " TO time,"+ policy + " Pr1 Met," + policy + " Pr2 Met," + policy + " Pr1 Slack," + policy + " Pr2 Slack," + policy + " Pr1 aff_pc," + policy + " Pr2 aff_pc"
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

                    ctime[policy]                   = 0
                    rtime[policy]                   = 0
                    ta_time[policy]                 = 0
                    to_time[policy]                 = 0

                    flag = 0
                    # print((str(sim_dir) + '/run_stdout_' + policy + "_arr_" + str(arr_scale) + '_stdvf_' + str(stdev_factor) + '.out'))
                    # with open(str(sim_dir) + '/run_stdout_' + policy + "_arr_" + str(arr_scale) + '_stdvf_' + str(stdev_factor)  + '_cpu_' + str(accel_count) + '.out','r') as fp:
                    #fname = str(sim_dir) + '/run_stdout_' + policy + "_arr_" + str(arr_scale) + '_stdvf_' + str(stdev_factor) + '.out'
                    fname = str(sim_dir) + '/run_stdout_' + policy + "_arr_" + str(arr_scale) + '_prob_' + str(prob) + '.out'
                    with open(fname,'r') as fp:
                        line = fp.readline()
                        while(line):
                            line = fp.readline()
                            if not line:
                                break
                            if (line == "Dropped,DAG ID,DAG Priority,DAG Type,Slack,Response Time,No-Affinity Time\n"):
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
                                dropped,tid,priority,dag_type,slack,resp,noafftime = line.split(',')
                                if priority == '1':
                                    cnt_1[policy] += 1
                                    if (int(dropped) == 1):
                                        cnt_dropped_1[policy] += 1
                                    else:
                                        if dag_type == '5':
                                            priority_1_slack[policy] += float(slack)/deadline_5
                                            if(float(slack) >= 0):
                                                priority_1_met[policy] += 1
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
                                            if(float(slack) >= 0):
                                                priority_2_met[policy] += 1
                                        else:
                                            if dag_type == '7':
                                                priority_1_slack[policy] += float(slack)/deadline_7 
                                            else: 
                                                priority_1_slack[policy] += float(slack)/deadline_10 
                                            if(float(slack) >= 0):
                                                priority_2_met[policy] += 1
                                        priority_2_noaff_per[policy] += float(noafftime)/float(resp)
                                        mission_time[policy] += float(resp)

                    if(cnt_1[policy] != cnt_dropped_1[policy]):
                        priority_1_slack[policy] = float(priority_1_slack[policy])/(cnt_1[policy]-cnt_dropped_1[policy])
                        priority_1_noaff_per[policy] = priority_1_noaff_per[policy]/(cnt_1[policy]-cnt_dropped_1[policy])
                    priority_2_slack[policy] = float(priority_2_slack[policy])/(cnt_2[policy]-cnt_dropped_2[policy])
                    priority_1_met[policy] = float(priority_1_met[policy])/cnt_1[policy]
                    priority_2_met[policy] = float(priority_2_met[policy])/cnt_2[policy]  

                    
                    priority_2_noaff_per[policy] = priority_2_noaff_per[policy]/(cnt_2[policy]-cnt_dropped_2[policy])  

                    mission_time[policy] += arr_scale*500*1000
                    out += ((",%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf,%lf") % (mission_time[policy],ctime[policy],rtime[policy],ta_time[policy],to_time[policy],priority_1_met[policy],priority_2_met[policy],priority_1_slack[policy],priority_2_slack[policy],priority_1_noaff_per[policy],priority_2_noaff_per[policy]))
                if(first):
                    print(header)
                    first = 0
                print(out)




if __name__ == "__main__":
   main(sys.argv[1])
