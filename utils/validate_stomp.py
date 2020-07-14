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
#  This is a slightly different version of the run_all.py script, used
#  to run validation tests that are then compared against their closed-
#  form (exact) counterparts (M/M/1, M/M/c, M/G/1, M/G/k, etc.).
#



from __future__ import print_function
from __future__ import division
from __builtin__ import str, True
import math
import os
import subprocess
import json
import time
import sys
import getopt
from sys import stdout
from subprocess import check_output
from collections import defaultdict


CONF_FILE      = 'utils/stomp_validation.json'
POLICY         = [ 'simple_policy_ver2' ]

MEAN_SER_TIME  = [ 10, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2100, 2200, 2300, 2400, 2500, 2600, 2700, 2800, 2900, 2990 ]  # units of time
COEFF_OF_VAR   = [ 0.01, 0.10 ]  # coefficient of variation (stdev / mean_ser_time)
MEAN_ARR_TIME  = [ 1000 ]  # units of time
SERVER_COUNT   = [ 3 ]

#MEAN_SER_TIME  = [ 1, 10, 20, 30, 40, 50, 60, 70, 80, 90, 99 ]  # units of time
#COEFF_OF_VAR   = [ 0.01 ]  # coefficient of variation (stdev / mean_ser_time)
#MEAN_ARR_TIME  = [ 100 ]  # units of time
#SERVER_COUNT   = [ 2, 4, 8, 16 ]


def usage_and_exit(exit_code):
    #stdout.write('\nusage: run_all.py [--help] [--verbose] [--csv-out] [--save-stdout] [--pre-gen-tasks] [--arrival-trace] [--input-trace] [--user-input-trace]\n\n')
    stdout.write('\nusage: %s [--help] [--verbose]\n\n' % (os.path.basename(__file__)))
    sys.exit(exit_code)



def main(argv):

    try:
        #opts, args = getopt.getopt(argv,"hvcspaiu",["help", "verbose", "csv-out", "save-stdout", "pre-gen-tasks", "arrival-trace", "input-trace", "user-input-trace"])
        opts, args = getopt.getopt(argv, "hv", ["help", "verbose"])
    except getopt.GetoptError:
        usage_and_exit(2)

    verbose               = False
    save_stdout           = False
    #pre_gen_tasks         = False
    #use_arrival_trace     = False
    #use_input_trace       = False
    #use_user_input_trace  = False
    #do_csv_output         = False
    #out_sep               = '\t'

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage_and_exit(0)
        elif opt in ("-v", "--verbose"):
            verbose = True
        #elif opt in ("-c", "--csv-out"):
        #    do_csv_output = True
        #    out_sep = ','
        #elif opt in ("-s", "--save-stdout"):
        #    save_stdout = True
        #elif opt in ("-p", "--pre-gen-tasks"):
        #    pre_gen_tasks = True
        #elif opt in ("-a", "--arrival-trace"):
        #    use_arrival_trace = True
        #elif opt in ("-i", "--input-trace"):
        #    use_input_trace = True
        #elif opt in ("-u", "--user-input-trace"):
        #    use_user_input_trace = True
        else:
            stdout.write('\nERROR: Unrecognized input parameter %s\n' % opt)
            usage_and_exit(3)
            
    #if (use_arrival_trace and use_input_trace):
    #    stdout.write('\nERROR: Cannot specify both arrival-trace and input-trace\n')
    #    usage_and_exit(argv[0], 4)
    #
    #if (use_arrival_trace and use_user_input_trace):
    #    stdout.write('\nERROR: Cannot specify both arrival-trace and user-input-trace\n')
    #    usage_and_exit(argv[0], 4)
    #
    #if (use_user_input_trace and use_input_trace):
    #    stdout.write('\nERROR: Cannot specify both use_user-input-trace and input-trace\n')
    #    usage_and_exit(argv[0], 4)

    # Simulation directory
    sim_dir = time.strftime("val_test_%d%m%Y_%H%M%S")
    if os.path.exists(sim_dir):
        shutil.rmtree(sim_dir)
    os.makedirs(sim_dir)

    # This dict is used to temporarily hold the output from the
    # different runs. Everything is dumped to files later on.
    sim_output = {}

    start_time = time.time()
    num_executions = 0

    # We open the JSON config file and update the corresponding
    # parameters directly in the stomp_params dicttionary
    with open(CONF_FILE) as conf_file:
        stomp_params = json.load(conf_file)

    stomp_params['general']['working_dir'] = os.getcwd() + '/' + sim_dir


    ###############################################################################################
    # MAIN LOOP

    first_time = True

    for mean_arr_time in MEAN_ARR_TIME:

        sim_output[mean_arr_time] = {}
        stomp_params['simulation']['mean_arrival_time'] = mean_arr_time

        for policy in POLICY:
            sim_output[mean_arr_time][policy] = {}

            for mean_ser_time in MEAN_SER_TIME:
                sim_output[mean_arr_time][policy][mean_ser_time] = {}

                for coeff_of_var in COEFF_OF_VAR:
                    sim_output[mean_arr_time][policy][mean_ser_time][coeff_of_var] = {}
                    
                    for server_count in SERVER_COUNT:
                        
                        sim_output[mean_arr_time][policy][mean_ser_time][coeff_of_var][server_count] = {}
                        sim_output[mean_arr_time][policy][mean_ser_time][coeff_of_var][server_count]['avg_resp_time'] = {}
        
        
                        ###########################################################################################
                        # Update the simulation configuration by updating
                        # the specific parameters in the input JSON data
                        stomp_params['simulation']['sched_policy_module'] = 'policies.' + policy
                        stomp_params['simulation']['servers']['dummy_server']['count'] = server_count
                        stomp_params['simulation']['tasks']['dummy_task']['mean_service_time']['dummy_server']  = mean_ser_time
                        stomp_params['simulation']['tasks']['dummy_task']['stdev_service_time']['dummy_server'] = coeff_of_var * mean_ser_time
        
                        stomp_params['general']['basename'] = 'policy:'  + policy              \
                                                            + '__arr:'   + str(mean_arr_time)  \
                                                            + '__mean:'  + str(mean_ser_time)  \
                                                            + '__cv:'    + str(coeff_of_var) \
                                                            + '__serv:'  + str(server_count)

                        conf_str = json.dumps(stomp_params)
        
                        ###########################################################################################
                        # Create command and execute the simulation
        
                        command = ['./stomp_main.py'
                                   + ' -c ' + CONF_FILE                      
                                   + ' -j \'' + conf_str + '\''
                                   ]
        
                        command_str = ' '.join(command)
        
                        #if (pre_gen_tasks):
                        #    command_str = command_str + ' -p'
                        #
                        #if (use_arrival_trace):
                        #    if (policy == POLICY[0]) and (stdev_factor == STDEV_FACTOR[0]):
                        #        command_str = command_str + ' -g generated_arrival_trace.trc'
                        #    else:
                        #        command_str = command_str + ' -a generated_arrival_trace.trc'
                        # 
                        #if (use_input_trace):
                        #    if (policy == POLICY[0]):
                        #        command_str = command_str + ' -g generated_trace_stdf_' + str(stdev_factor) + '.trc'
                        #    else:
                        #        command_str = command_str + ' -i generated_trace_stdf_' + str(stdev_factor) + '.trc'
                        # 
                        #if (use_user_input_trace):
                        #    command_str = command_str + ' -i ../user_traces/user_gen_trace_stdf_' + str(stdev_factor) + '.trc'

                        if (verbose):
                            print('Running', command_str)
        
                        sys.stdout.flush()
                        output = subprocess.check_output(command_str, stderr=subprocess.STDOUT, shell=True)
        
                        if (save_stdout):
                            fh = open(sim_dir + '/run_stdout_' + policy + '_arr_' + str(mean_arr_time) + '_mean_' + str(mean_ser_time)
                                      + '_cv_' + str(coeff_of_var) + '_serv_' + str(server_count) + '.out', 'w')
        
                        ###########################################################################################
                        # Parse the output line by line
                        output_list = output.splitlines()
                        i = 0
                        for i in range(len(output_list)):
                            
                            if (save_stdout):
                                fh.write('%s\n' % (output_list[i]))

                            if output_list[i].strip() == "Busy time and Utilization:":
                                avg_util = 0.0
                                for j in range(server_count):
                                    line = output_list[i+2+j].strip()
                                    avg_util = avg_util + float(line.split()[-1]) / 100.0
                                avg_util = avg_util / server_count
                                stdout.write('%.4f\n' % (avg_util))
                                
                            if output_list[i].strip() == "Waiting time (avg):":
                                line = output_list[i+1].strip()
                                (key, value) = line.split(':')
                                simulated_waiting_time = value.strip().split(' ')[0]
                                
                                # We model the waiting time using the
                                # closed-formed expression of M/G/k queues
                                lamb  = 1 / mean_arr_time
                                mu    = 1 / mean_ser_time
                                rho   = lamb / mu
                                
                                tmp   = rho / server_count
                                scv   = coeff_of_var**2
                                stdev = coeff_of_var * mean_ser_time
                                var   = stdev**2
                                
                                if (tmp >= 1.0):
                                    stdout.write('WARNING: rho/c = %.2f >= 1.0! Skipping...\n' % (tmp))
                                
                                else:
                                    modeled_waiting_time_1 = compute_waiting_time_MGk(scv, server_count, lamb, mu)
                                    error = 100.0 * abs(float(simulated_waiting_time)-modeled_waiting_time_1) / modeled_waiting_time_1
                                    
                                    modeled_waiting_time_2 = -1.0
                                    if (server_count == 1):
                                        modeled_waiting_time_2 = compute_waiting_time_MG1(lamb, mu, mean_ser_time, var)
                                    
                                    if (first_time):
                                        first_time = False
                                        stdout.write('Policy\tArr Time (mean)\tServ Time (mean)\tCV\tServers\tSimulated Wait Time\tError (%)\tModeled Wait Time 1\tModeled Wait Time 2\trho/c\tSCV\tSimulated Utilization\n')
                                    stdout.write('%s\t%.4f\t%.4f\t%.4f\t%d\t%s\t%.4f\t%.4f\t%.4f\t%.4f\t%.4f\t' % (policy, mean_arr_time, mean_ser_time, coeff_of_var, server_count, simulated_waiting_time, error, modeled_waiting_time_1, modeled_waiting_time_2, tmp, scv))
                                    
                        if (save_stdout):
                            fh.close()
                        num_executions += 1
                        time.sleep(1)


    ###############################################################################################
    # Dump outputs to files

    # Average respose time
    #if (do_csv_output):
    #    fh = open(sim_dir + '/avg_resp_time.csv', 'w')
    #else:
    #    fh = open(sim_dir + '/avg_resp_time.out', 'w')
    #first_time = True
    #for mean_arr_time in MEAN_ARR_TIME:
    #    #fh.write('Arrival_Time %lf\n' % mean_arr_time)
    #    for policy in sorted(sim_output[mean_arr_time].iterkeys()):
    #        #fh.write('%s\n' % policy)
    #        #first_time = True
    #        for stdev_factor in sorted(sim_output[mean_arr_time][policy].iterkeys()):
    #            for server_count in sorted(sim_output[mean_arr_time][policy][stdev_factor].iterkeys()):                    
    #                if first_time:
    #                    # Print header
    #                    fh.write('  Arr_time%s Policy%s Stdev_Factor%s Servers%s' % (out_sep, out_sep, out_sep, out_sep))
    #                    for key in sorted(sim_output[mean_arr_time][policy][stdev_factor][server_count]['avg_resp_time'].iterkeys()):
    #                        fh.write('%s%s%s%s%s' % (key, out_sep, out_sep, out_sep, out_sep))
    #                    fh.write('\n')
    #                    first_time = False
    #                # Print values
    #                fh.write('  %s%s%s%s%s%s%s%s' % (str(mean_arr_time), out_sep, policy, out_sep, str(stdev_factor), out_sep, str(server_count), out_sep))
    #                for key in sorted(sim_output[mean_arr_time][policy][stdev_factor][server_count]['avg_resp_time'].iterkeys()):
    #                    tl = sim_output[mean_arr_time][policy][stdev_factor][server_count]['avg_resp_time'][key].split()
    #                    for tt in tl:
    #                        fh.write('%s%s' % (tt, out_sep))
    #                fh.write('\n')
    #        #fh.write('\n\n')
    #fh.close()

    # Queue size histogram
    #if (do_csv_output):
    #    fh = open(sim_dir + '/queue_size_hist.csv', 'w')
    #else:
    #    fh = open(sim_dir + '/queue_size_hist.out', 'w')
    #for arr_scale in ARRIVE_SCALE:
    #    fh.write('Arrival_Scale %lf\n' % arr_scale)
    #    for policy in sorted(sim_output[arr_scale].iterkeys()):
    #        fh.write('%s\n' % policy)
    #        fh.write('  Arr_Scale%sStdev_Factor%sQueue_Histogram\n' % (out_sep, out_sep))
    #        for stdev_factor in sorted(sim_output[arr_scale][policy].iterkeys()):
    #            fh.write('  %s%s%s%s' % (str(arr_scale), out_sep, str(stdev_factor), out_sep))
    #            tl = sim_output[arr_scale][policy][stdev_factor]['queue_size_hist'].replace(',',' ').split()
    #            for tt in tl:
    #                fh.write('%s%s' % (tt, out_sep))
    #            fh.write('\n')
    #    fh.write('\n\n')
    #fh.close()

    # Total Simulation Time
    #if (do_csv_output):
    #    fh = open(sim_dir + '/total_sim_time.csv', 'w')
    #else:
    #    fh = open(sim_dir + '/total_sim_time.out', 'w')
    #for arr_scale in ARRIVE_SCALE:
    #    fh.write('Arrival_Scale %lf\n' % arr_scale)
    #    for policy in sorted(sim_output[arr_scale].iterkeys()):
    #        fh.write('%s\n' % policy)
    #        fh.write('  Arr_Scale%sStdev_Factor%sTotal_Sim_Time\n' % (out_sep, out_sep))
    #        for stdev_factor in sorted(sim_output[arr_scale][policy].iterkeys()):
    #            fh.write('  %s%s%s%s' % (str(arr_scale), out_sep, str(stdev_factor), out_sep))
    #            tl = sim_output[arr_scale][policy][stdev_factor]['total_sim_time'].replace(',',' ').split()
    #            for tt in tl:
    #                fh.write('%s%s' % (tt, out_sep))
    #            fh.write('\n')
    #    fh.write('\n\n')
    #fh.close()

    elapsed_time = time.time() - start_time
    stdout.write('%d configurations executed in %.2f secs.\nResults written to %s\n' % (num_executions, elapsed_time, sim_dir))


def compute_waiting_time_MMc(c, lamb, mu):
    
    rho = lamb / mu
    #stdout.write('lambda=%.2f, mu=%.2f, rho=%.2f, rho/c=%.2f\n' % (lamb, mu, rho, rho/c))
    
    p0_inv = 1 + rho**c / ( math.factorial(c) * (1-(rho/c)) )
    for i in range(1,c):
        p0_inv = p0_inv + (rho**i) / math.factorial(i)
    
    p0 = 1/p0_inv
    
    queue_length = (rho**(c+1))*p0/(math.factorial(c-1)*(c-rho)**2)
    waiting_time = queue_length/lamb
    return waiting_time


def compute_waiting_time_MGk(scv, c, lamb, mu):
    
    waiting_time = ((scv + 1) / 2) * compute_waiting_time_MMc(c, lamb, mu)
    
    return waiting_time


def compute_waiting_time_MG1(lamb, mu, mean_ser_time, var):
    
    rho = lamb / mu
    tmp = var + mean_ser_time**2
    
    waiting_time = (lamb * tmp) / (2 * (1-rho))
    
    return waiting_time



if __name__ == "__main__":
   main(sys.argv[1:])
