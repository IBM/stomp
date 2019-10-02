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


CONF_FILE    = './stomp.json'
CONF_FILE    = './stomp.json'
POLICY       = ['simple_policy_ver4', 'simple_policy_ver5', 'simple_policy_ver7', 'simple_policy_ver8']
# POLICY       = ['simple_policy_ver1', 'simple_policy_ver2', 'simple_policy_ver3', 'simple_policy_ver4', 'simple_policy_ver5', 'simple_policy_ver6']
STDEV_FACTOR = [0.01] #, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]  # percentages
# STDEV_FACTOR = [ 0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]  # percentages
ARRIVE_SCALE = [0.26, 0.28, 0.3, 0.32, 0.34] #, 0.4, 0.6, 0.7, 0.8, 0.9, 1.1, 1.2]  # percentages
#ARRIVE_SCALE = [ 0.35, 0.36 , 0.37, 0.38, 0.39, 0.4, 0.41, 0.42, 0.43, 0.44, 0.45 ]  # percentages
# ARRIVE_SCALE = [ 0.2, 0.22, 0.24 , 0.26, 0.28, 0.3, 0.32, 0.34, 0.36, 0.38, 0.4] #, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 2]  # percentages
# ARRIVE_SCALE = [ 0.1, 0.2 , 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 2]  # percentages




deadline_5 = 1100
deadline_10 = 1300

def main(argv):
    sim_dir = argv
    first = 1
    for arr_scale in ARRIVE_SCALE:
        for accel_count in range(5,6):

            priority_1_slack = {}
            priority_1_met = {}

            priority_2_slack = {}
            priority_2_met = {}
            
            cnt_1 = {}
            cnt_2 = {}
            cnt_dropped_1 = {}
            cnt_dropped_2 = {}

            header = "ACCEL_COUNT,ARR_SCALE,STDEV_FACTOR"
            out = str(accel_count) + "," + str(arr_scale)
            for stdev_factor in STDEV_FACTOR:
                out += "," + str(stdev_factor) 
                for policy in POLICY:
                    header = header + "," + policy + " Pr1 slack," + policy + " Pr2 slack," + policy + " Pr1 Met," + policy + " Pr2 Met"
                    priority_1_slack[policy] = 0
                    priority_1_met[policy] = 0
                    cnt_1[policy] = 0
                    priority_2_slack[policy] = 0
                    priority_2_met[policy] = 0
                    cnt_2[policy] = 0   
                    cnt_dropped_1[policy] = 0   
                    cnt_dropped_2[policy] = 0   

                    flag = 0
                    # print((str(sim_dir) + '/run_stdout_' + policy + "_arr_" + str(arr_scale) + '_stdvf_' + str(stdev_factor) + '.out'))
                    with open(str(sim_dir) + '/run_stdout_' + policy + "_arr_" + str(arr_scale) + '_stdvf_' + str(stdev_factor)  + '_cpu_' + str(accel_count) + '.out','r') as fp:
                        line = fp.readline()
                        while(line):
                            line = fp.readline()
                            if (line == "TID,Priority,Type,SLACK\n"):
                                flag = 1
                                continue

                            if (flag):
                                if(cnt_1[policy] + cnt_2[policy] >= 1000):
                                    break
                                # print(line)
                                dropped,tid,priority,dag_type,slack = line.split(',')
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
                                            priority_1_slack[policy] += float(slack)/deadline_10 
                                            if(float(slack) >= 0):
                                                priority_1_met[policy] += 1
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
                                            priority_2_slack[policy] += float(slack)/deadline_10
                                            if(float(slack) >= 0):
                                                priority_2_met[policy] += 1
                

                    priority_1_slack[policy] = float(priority_1_slack[policy])/(cnt_1[policy]-cnt_dropped_1[policy])
                    priority_2_slack[policy] = float(priority_2_slack[policy])/(cnt_2[policy]-cnt_dropped_2[policy])
                    priority_1_met[policy] = float(priority_1_met[policy])/cnt_1[policy]
                    priority_2_met[policy] = float(priority_2_met[policy])/cnt_2[policy]             
                    out += ((",%lf,%lf,%lf,%lf") % (priority_1_slack[policy],priority_2_slack[policy],priority_1_met[policy],priority_2_met[policy]))
                if(first):
                    print(header)
                    first = 0
                print(out)




if __name__ == "__main__":
   main(sys.argv[1])
