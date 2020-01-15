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

from run_all_2 import POLICY, STDEV_FACTOR, ARRIVE_SCALE


def main(argv):
    sim_dir = argv
    first = 1
    for arr_scale in ARRIVE_SCALE:

        cnt = {}
        resp = {}

        header = "ARR_SCALE,STDEV_FACTOR"
        out = str(arr_scale)
        for stdev_factor in STDEV_FACTOR:
            out += "," + str(stdev_factor) 
            for policy in POLICY:
                header = header + "," + policy + " Avg Response Time"
                cnt[policy] = 0  
                resp[policy] = 0

                flag = 0
                fname = str(sim_dir) + '/run_dag_' + policy + "_arr_" + str(arr_scale) + '_stdvf_' + str(stdev_factor) + '.csv'

                with open(fname,'r') as fp:
                    for line in fp.readlines():
                        # print(line)
                        if not line:
                            break
                        if (line == "DAG ID,DAG Type,Response Time\n"):
                            flag = 1
                            continue

                        if (flag):
                            if(cnt[policy] >= 1000):
                                break

                            cnt[policy] += 1
                            tid,dag_type,response = line.split(',')
                            resp[policy] += float(response)
                        line = fp.readline()
                
                resp[policy] = resp[policy]/cnt[policy]

                out += ((",%lf") % (resp[policy]))
            if(first):
                print(header)
                first = 0
            print(out)




if __name__ == "__main__":
   main(sys.argv[1])
