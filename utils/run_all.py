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
import shutil
import getopt
import numpy as np
from sys import stdout
from subprocess import check_output
from collections import defaultdict
from builtins import str

JOBS_LIM = 32

PWR_MGMT     = [False]
PTOKS        = [100000] # [6500, 7000, 7500, 8000, 8500, 9000, 9500, 10000] # , 10500, 11000, 11500, 12000, 12500, 13000, 13500, 14000, 14500, 15000, 100000]
# SLACK_PERC   = [0.0, 98.4]
SLACK_PERC   = np.linspace(0, 100, 50, endpoint=True).tolist()
folder = ""

CONF_FILE        = None #Automatically set based on app
PROMOTE          = True
CONTENTION       = [True] #, False]

APP              = ['synthetic', 'ad', 'mapping', 'package']
POLICY_SOTA      = ['ads', 'edf_eft', 'rheft', 'heft']
POLICY_NEW       = ['ts_eft','ms1_hom','ms1_hetero','ms1_hyb', 'ms1_hyb_update', 'ms2_hom','ms2_hetero','ms2_hyb', 'ms2_hyb_update']
POLICY           = POLICY_SOTA + POLICY_NEW
#NEW
ARRIVE_SCALE0     = [0.2, 0.2, 0.2, 1.0] # synthetic, ad
ARRIVE_SCALE1     = [0.1, 0.1, 0.1, 0.1] # mapping
ARRIVE_SCALE2     = [0.1, 0.1, 0.1, 0.1] # package

#SOTA
ARRIVE_SCALE3    = [0.2, 0.2, 0.2, 1.0] # synthetic, ad
ARRIVE_SCALE4    = [0.1, 0.1, 0.1, 0.1] # mapping
ARRIVE_SCALE5    = [0.1, 0.1, 0.1, 0.1] # package
PROB             = [0.1, 0.2, 0.3, 0.5]
DROP             = [False, True]

RUNS = 1#32#50
DELTA = 0.5#5#1.0

total_count = len(APP) * len(POLICY) * len(ARRIVE_SCALE0) * len(PROB) * len(DROP)
print("Total jobs launched: {}".format(total_count))

def usage_and_exit(exit_code):
    stdout.write('\nusage: run_all.py [--help] [--verbose] [--csv-out] [--save-stdout] [--user-input-trace] [--user-input-trace-debug] [--run_hetero]\n\n')
    sys.exit(exit_code)

def main(argv):
    try:
        opts, args = getopt.getopt(argv,"hvcsudr",["help", "verbose", "csv-out", "save-stdout", "user-input-trace", "user-input-trace-debug","run_hetero"])
    except getopt.GetoptError:
        usage_and_exit(2)

    verbose               = False
    save_stdout           = False
    use_user_input_trace  = False
    trace_debug           = False
    do_csv_output         = False
    out_sep               = '\t'
    run                   = ''
    ACCEL_COUNT           = 1

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage_and_exit(0)
        elif opt in ("-v", "--verbose"):
            verbose = True
        elif opt in ("-c", "--csv-out"):
            do_csv_output = True
            out_sep = ','
        elif opt in ("-s", "--save-stdout"):
            save_stdout = True
        elif opt in ("-u", "--user-input-trace"):
            use_user_input_trace = True
        elif opt in ("-d", "--user-input-trace-debug"):
            trace_debug = True
        elif opt in ("-r", "--run_hetero"):
            run = 'hetero'
            ACCEL_COUNT = 6
        else:
            stdout.write('\nERROR: Unrecognized input parameter %s\n' % opt)
            usage_and_exit(3)

    process = []
    run_count = 0
    # Simulation directory
    for app in APP:
        sim_dir = time.strftime("sim_%d%m%Y_%H%M%S") + "_" + str(app)
        if os.path.exists(sim_dir):
            shutil.rmtree(sim_dir)
        os.makedirs(sim_dir)

        # This dict is used to temporarily hold the output from the
        # different runs. Everything is dumped to files later on.
        sim_output = {}

        start_time = time.time()
        num_executions = 0
        first_time = True

        # We open the JSON config file and update the corresponding
        # parameters directly in the stomp_params dicttionary
        if app == "synthetic":
            CONF_FILE = './inputs/stomp.json'
        else:
            CONF_FILE = './inputs/stomp_real.json'

        with open(CONF_FILE) as conf_file:
            stomp_params = json.load(conf_file)

        stomp_params['general']['working_dir'] = os.getcwd() + '/' + sim_dir


        ###############################################################################################
        # MAIN LOOP
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
                        for x in range(0,len(PROB)):
                            print(x)
                            prob = PROB[x]
                            ARRIVE_SCALE = []

                            #for arr_scale in ARRIVE_SCALE:
                            for y in range(0,RUNS):

                                for policy in POLICY:

                                    if (policy in POLICY_SOTA):
                                        if(app == "synthetic" or app == "ad"):
                                            ARRIVE_SCALE = ARRIVE_SCALE3
                                        elif(app == "mapping"):
                                            ARRIVE_SCALE = ARRIVE_SCALE4
                                        elif(app == "package"):
                                            ARRIVE_SCALE = ARRIVE_SCALE5

                                    else:
                                        if(app == "synthetic" or app == "ad"):
                                            ARRIVE_SCALE = ARRIVE_SCALE0
                                        elif(app == "mapping"):
                                            ARRIVE_SCALE = ARRIVE_SCALE1
                                        elif(app == "package"):
                                            ARRIVE_SCALE = ARRIVE_SCALE2

                                    arr_scale = ARRIVE_SCALE[x] + DELTA*y
                                    print("Prob: " + str(prob) + "arr_scale: " + str(arr_scale))
                                    if (policy in POLICY_SOTA and (drop == True)):
                                            print("No dropping for SOTA/Not arr_scale", policy, drop, arr_scale)
                                            continue

                                    # print(ARRIVE_SCALE0+ARRIVE_SCALE2)
                                    # if (policy in POLICY_NEW and (drop == False)):
                                    #     print("Only dropping for NEW/Not arr_scale", policy, drop, arr_scale)
                                    #     continue

                                    print("Running", policy, drop, arr_scale, run_count)

                                    for ptoks in PTOKS_:
                                        sim_output[arr_scale] = {}
                                        stomp_params['simulation']['pwr_mgmt'] = pwr_mgmt
                                        stomp_params['simulation']['total_ptoks'] = ptoks
                                        stomp_params['simulation']['slack_perc'] = slack_perc
                                        stomp_params['simulation']['arrival_time_scale'] = arr_scale

                                        first_flag = False
                                        for accel_count in [0, 2, 4, 8]: #range(0,10,2):
                                            for cpu_count in [2, 4, 8]: #range(2,10,2):
                                                for gpu_count in [0, 2, 4, 8]: #range(0,10,2):
                                                    if(run == 'hetero'):
                                                        stomp_params['simulation']['servers']['cpu_core']['count'] = cpu_count
                                                        if(app == "mapping" or app == "package"):
                                                            stomp_params['simulation']['servers']['loc_accel']['count'] = accel_count
                                                        if(app == "ad"):
                                                            stomp_params['simulation']['servers']['det_accel']['count'] = accel_count
                                                            stomp_params['simulation']['servers']['loc_accel']['count'] = accel_count
                                                            stomp_params['simulation']['servers']['tra_accel']['count'] = accel_count
                                                        stomp_params['simulation']['servers']['gpu']['count'] = gpu_count
                                                        print("Running for A: %d G:%d C:%d count:" %(accel_count, gpu_count,cpu_count))
                                                    else:
                                                        if(first_flag):
                                                            continue
                                                        first_flag = True

                                                    run_count += 1
                                                    sim_output[arr_scale][policy] = {}

                                                    stomp_params['simulation']['drop']         = drop
                                                    stomp_params['simulation']['contention']   = cont
                                                    stomp_params['simulation']['promote']      = PROMOTE

                                                    sim_output[arr_scale][policy] = {}
                                                    sim_output[arr_scale][policy]['avg_resp_time'] = {}
                                                    sim_output[arr_scale][policy]['met_deadline'] = {}

                                                    ###########################################################################################
                                                    # Update the simulation configuration by updating
                                                    # the specific parameters in the input JSON data
                                                    stomp_params['simulation']['application'] = app
                                                    stomp_params['simulation']['policy'] = policy
                                                    print(stomp_params['simulation']["policies"][policy])
                                                    stomp_params['simulation']['sched_policy_module'] = 'task_policies.' + stomp_params['simulation']["policies"][policy]["task_policy"]
                                                    stomp_params['simulation']['meta_policy_module'] = 'meta_policies.' + stomp_params['simulation']["policies"][policy]["meta_policy"]

                                                    stomp_params['general']['basename'] = policy + \
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
                                                    conf_str = json.dumps(stomp_params)

                                                    ###########################################################################################
                                                    # Create command and execute the simulation

                                                    command = ['./simulator/stomp_main.py'
                                                               + ' -c ' + CONF_FILE
                                                               + ' -j \'' + conf_str + '\''
                                                               ]

                                                    command_str = ' '.join(command)

                                                    command_str = command_str + ' -i ../inputs/' + str(app) + '/trace_files/' + str(app) + '_trace_' + str(prob) + '.trc'
                                                    if (verbose):
                                                        print('Running', command_str)

                                                    sys.stdout.flush()
                                                    # output = subprocess.check_output(command_str, stderr=subprocess.STDOUT, shell=True)
                                                    stdout_fname=sim_dir + "/out_" + stomp_params['general']['basename']
                                                    with open(stdout_fname, 'wb') as out:
                                                        print("Running command")
                                                        p = subprocess.Popen(command_str, stdout=out, stderr=subprocess.STDOUT, shell=True)
                                                        process.append(p)
                                                        print("Process count now: {} (lim {})".format(len(process), JOBS_LIM))
                                                        if len(process) >= JOBS_LIM:
                                                            print(str(run_count) + "/" + str(total_count))
                                                            for p in process:
                                                                p.wait()
                                                            del process[:]

    for p in process:
        p.wait()

if __name__ == "__main__":
   main(sys.argv[1:])
