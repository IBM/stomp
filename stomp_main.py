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

import sys, getopt
import importlib
import json
import collections
import threading

from stomp import STOMP
from meta import META


def usage_and_exit(exit_code):
    print 'usage: stomp_main.py [--help] [--debug] [--conf-file=<json_config_file>] [--conf-json=<json_string>] [--input-trace=<string>] '
    sys.exit(exit_code)


def update(d, u):
    for k, v in u.iteritems():
        if (k in d):
            if isinstance(v, collections.Mapping):
                r = update(d.get(k, {}), v)
                d[k] = r
            else:
                d[k] = u[k]
    return d


def main(argv):

    try:
        opts, args = getopt.getopt(argv,"hdpc:j:i:",["help", "conf-file=", "conf-json=", "debug", "input-trace="])
    except getopt.GetoptError:
        usage_and_exit(2)

    conf_file = "stomp.json"
    conf_json = None
    log_level = None
    input_trace_file = None

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage_and_exit(0)
        elif opt in ("-c", "--conf-file"):
            conf_file = arg
        elif opt in ("-j", "--conf-json"):
            conf_json = json.loads(arg)
        elif opt in ("-i", "--input-trace"):
            input_trace_file = arg
        elif opt in ("-d", "--debug"):
            log_level = "DEBUG"

    with open(conf_file) as conf_file:
        stomp_params = json.load(conf_file)
    if (conf_json):
        # We update configuration parameters with JSON
        # values received through the command line
        update(stomp_params, conf_json)
    
    # Dinamically import the scheduling policy class
    sched_policy_module = importlib.import_module(stomp_params['simulation']['sched_policy_module'])

    if (log_level):
        stomp_params['general']['logging_level'] = log_level

    #print('Setting input_arr_tr file to %s\n' % (input_trace_file))
    stomp_params['general']['input_trace_file'] = input_trace_file

    # Instantiate and run STOMP, print statistics
    stomp_sim = STOMP(stomp_params, sched_policy_module.SchedulingPolicy())
    meta_sim = META(stomp_params,stomp_sim)

    thread1 = threading.Thread(target=meta_sim.run)
    thread2 = threading.Thread(target=stomp_sim.run)
    
    # Will execute both in parallel
    thread1.start()
    thread2.start()

    thread1.join()
    thread2.join()

    stomp_sim.print_stats()


if __name__ == "__main__":
   main(sys.argv[1:])
