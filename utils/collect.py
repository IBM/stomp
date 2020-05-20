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
#  This script is used to collect data for large number of tests run using 
#  run_all.py 
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

from run_all import POLICY, STDEV_FACTOR, ARRIVE_SCALE

extra = True

conf_file = "stomp.json"
stomp_params = {}
with open(conf_file) as conf_file:
    stomp_params = json.load(conf_file)

mean_arrival_time = stomp_params['simulation']['mean_arrival_time']


deadline_5 = 537
deadline_7 = 428
deadline_10 = 1012


def main(argv):
    sim_dir = argv
    header = "Arrival Scale,Stdev Factor,Policy,Mission time,Mission Completed,Met,Cnt"
    if (extra):
        header = header + ",Slack"
    print(header)
    for stdev_factor in STDEV_FACTOR:
        for arr_scale in ARRIVE_SCALE:
            cnt                     = {}
            slack                   = {}
            met                     = {}
            mission_time            = {}
            mission_completed       = {}

            out = str(arr_scale) + "," + str(stdev_factor) 
            for policy in POLICY:
                slack[policy]                   = 0
                met[policy]                     = 0
                cnt[policy]                     = 0   
                mission_time[policy]            = 0
                mission_completed[policy]       = 0
                mission_failed                  = 0
                

                flag = 0
                fname = str(sim_dir) + '/run_dag_' + policy + "_arr_" + str(arr_scale) + '_stdvf_' + str(stdev_factor) + '.csv'
                if os.path.exists(fname):
                    pass
                else:

                    out2 = str(arr_scale) + "," + str(stdev_factor) + "," + str(policy) 
                    print(out2 + ",NodataYet")
                    continue

                with open(fname,'r') as fp:
                    for line in fp.readlines():
                        # if not line:
                        #     break
                        if (line == "DAG ID,DAG Type,Slack,Response Time,Energy\n"):
                            flag = 1
                            continue

                        if (flag):
                            # if(cnt[policy] >= 1000):
                            #     break
                            
                            tid,dag_type,dag_slack,resp,energy = line.split(',')

                            cnt[policy] += 1
                            
                            if dag_type == '5':
                                slack[policy] += float(dag_slack)/deadline_5
                            if dag_type == '7':
                                slack[policy] += float(dag_slack)/deadline_7 
                            if dag_type == '10': 
                                slack[policy] += float(dag_slack)/deadline_10

                            if(float(dag_slack) >= 0):
                                met[policy] += 1
                            elif(mission_failed != 1):
                                mission_failed = 1
                                mission_completed[policy] = met[policy]
                            
                            mission_time[policy] += float(resp)


                slack[policy] = float(slack[policy])/(cnt[policy])
                met[policy] = float(met[policy])/cnt[policy]  

                mission_completed[policy] = float(mission_completed[policy])/cnt[policy]
                if mission_failed == 0:
                    mission_completed[policy] = 1.0;

                out = str(arr_scale) + "," + str(stdev_factor) + "," + str(policy) 
                out += ((",%lf,%lf,%lf,%d") % (mission_time[policy], mission_completed[policy],met[policy],cnt[policy]))
                if(extra):
                    out += ((",%lf") % (slack[policy]))

                print(out)


if __name__ == "__main__":
   main(sys.argv[1])
