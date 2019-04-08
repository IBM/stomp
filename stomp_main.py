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
from stomp import STOMP


def usage_and_exit(exit_code):
    print 'usage: stomp_main.py [--help] [--conf-file=<json_config_file>] [--conf-json=<json_string>]'
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
        #opts, args = getopt.getopt(argv,"hg:l:c:w:o:j:",["help", "gui=", "log-file=", "conf-file=", "work-dir=", "out-file=", "conf-json="])
        opts, args = getopt.getopt(argv,"hdc:j:",["help", "conf-file=", "conf-json="])
    except getopt.GetoptError:
        usage_and_exit(2)

    conf_file = "stomp.json"
    conf_json = None
    log_level = None
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage_and_exit(0)
        elif opt in ("-c", "--conf-file"):
            conf_file = arg
        elif opt in ("-j", "--conf-json="):
            conf_json = json.loads(arg)
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
        stomp_params['general']['logging_level'] = log_level;
    
    # Instantiate and run STOMP, print statistics
    stomp_sim = STOMP(stomp_params, sched_policy_module.SchedulingPolicy())
    stomp_sim.run()
    stomp_sim.print_stats()


if __name__ == "__main__":
   main(sys.argv[1:])
