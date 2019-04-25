#!/usr/bin/env python

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
POLICY       = ['simple_policy_ver1', 'simple_policy_ver2', 'simple_policy_ver3']
STDEV_FACTOR = [0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]  # percentages


def usage_and_exit(exit_code):
    stdout.write('\nusage: run_all.py [--help] [--verbose] [--save_stdout] [--pre-gen-tasks] [--arrival-trace]\n\n')
    sys.exit(exit_code)



def main(argv):

    try:
        opts, args = getopt.getopt(argv,"hvspa",["help", "verbose", "save-stdout", "pre-gen-tasks", "arrival_trace"])
    except getopt.GetoptError:
        usage_and_exit(2)

    verbose           = False
    save_stdout       = False
    pre_gen_tasks     = False
    use_arrival_trace = False

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage_and_exit(0)
        elif opt in ("-v", "--verbose"):
            verbose = True
        elif opt in ("-s", "--save-stdout"):
            save_stdout = True
        elif opt in ("-p", "--pre-gen-tasks"):
            pre_gen_tasks = True
        elif opt in ("-a", "--arrival-trace"):
            use_arrival_trace = True


    # Simulation directory
    sim_dir = time.strftime("sim_%d%m%Y_%H%M%S")
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
    with open(CONF_FILE) as conf_file:
        stomp_params = json.load(conf_file)

    stomp_params['general']['working_dir'] = os.getcwd() + '/' + sim_dir


    ###############################################################################################
    # MAIN LOOP
    for policy in POLICY:

        sim_output[policy] = {}

        for stdev_factor in STDEV_FACTOR:

            sim_output[policy][stdev_factor] = {}
            sim_output[policy][stdev_factor]['avg_resp_time'] = {}


            ###########################################################################################
            # Update the simulation configuration by updating
            # the specific parameters in the input JSON data
            stomp_params['simulation']['sched_policy_module'] = 'policies.' + policy 
            for task in stomp_params['simulation']['tasks']:
                # Set the stdev for the service time
                for server, mean_service_time in stomp_params['simulation']['tasks'][task]['mean_service_time'].items():
                    stdev_service_time = int(round(stdev_factor*mean_service_time))
                    stomp_params['simulation']['tasks'][task]['stdev_service_time'][server] = stdev_service_time

            stomp_params['general']['basename'] = 'policy:' + policy \
                                            + '__stdev_factor:' + str(stdev_factor)
            conf_str = json.dumps(stomp_params)

            ###########################################################################################
            # Create command and execute the simulation
            
            command = ['./stomp_main.py'                       
                       + ' -j \'' + conf_str + '\''
                       ]

            command_str = ' '.join(command)

            if (pre_gen_tasks):
                command_str = command_str + ' -p'

            if (use_arrival_trace):
                if (policy == POLICY[0]) and (stdev_factor == STDEV_FACTOR[0]):
                    command_str = command_str + ' -g generated_arrival_trace.trc'
                else:
                    command_str = command_str + ' -a generated_arrival_trace.trc'
            
            if (verbose):
                print('Running', command_str)

            sys.stdout.flush()
            output = subprocess.check_output(command_str, stderr=subprocess.STDOUT, shell=True)

            if (save_stdout):
                fh = open(sim_dir + '/run_stdout_' + policy + '_stdvf_' + str(stdev_factor) + '.out', 'w')

            ###########################################################################################
            # Parse the output line by line
            output_list = output.splitlines()
            i = 0
            for i in range(len(output_list)):
                if (save_stdout):
                    fh.write('%s\n' % (output_list[i]))
                if output_list[i].strip() == "Response time (avg):":
                    for j in range(i+1, len(output_list)):
                        line = output_list[j]
                        if not line.strip():
                            break
                        (key, value) = line.split(':')
                        sim_output[policy][stdev_factor]['avg_resp_time'][key.strip()] = value.strip()


                elif output_list[i].strip() == "Histograms:":
                    line = output_list[i+1]
                    histogram = line.split(':')[1]
                    sim_output[policy][stdev_factor]['queue_size_hist'] = histogram.strip()

            if (save_stdout):
                fh.close()
            num_executions += 1
            time.sleep(1)


    ###############################################################################################
    # Dump outputs to files

    # Average respose time
    fh = open(sim_dir + '/avg_resp_time.out', 'w')
    for policy in sorted(sim_output.iterkeys()):
        fh.write('%s\n' % policy)
        first_time = True
        for stdev_factor in sorted(sim_output[policy].iterkeys()):
            if first_time:
                # Print header
                fh.write('  Stdev_Factor\t')
                for key in sorted(sim_output[policy][stdev_factor]['avg_resp_time'].iterkeys()):
                    fh.write(',%s\t\t\t' % key)
                fh.write('\n')
                first_time = False
            # Print values
            fh.write('  %s\t' % str(stdev_factor))
            for key in sorted(sim_output[policy][stdev_factor]['avg_resp_time'].iterkeys()):
                fh.write('%s\t' % sim_output[policy][stdev_factor]['avg_resp_time'][key])
            fh.write('\n')
        fh.write('\n\n')
    fh.close()

    # Queue size histogram
    fh = open(sim_dir + '/queue_size_hist.out', 'w')
    for policy in sorted(sim_output.iterkeys()):
        fh.write('%s\n' % policy)
        for stdev_factor in sorted(sim_output[policy].iterkeys()):
            fh.write('  %s\t%s\n' % (str(stdev_factor), sim_output[policy][stdev_factor]['queue_size_hist']))
    fh.write('\n\n')
    fh.close()


    elapsed_time = time.time() - start_time
    stdout.write('%d configurations executed in %.2f secs.\nResults written to %s\n' % (num_executions, elapsed_time, sim_dir))




if __name__ == "__main__":
   main(sys.argv[1:])
