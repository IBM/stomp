#!/usr/bin/env python3
#
# Copyright 2022 IBM
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
import simpy
import argparse
from collections import abc
import threading

from stomp import STOMP
from meta import META

import utils
from utils import SharedObjs

def usage_and_exit(exit_code):
    print('usage: stomp_main.py [--help] [--debug] [--conf-file=<json_config_file>] [--conf-json=<json_string>] [--input-trace=<string>] ')
    sys.exit(exit_code)

def update(d, u):
    for k, v in u.items():
        if (k in d):
            if isinstance(v, abc.Mapping):
                r = update(d.get(k, {}), v)
                d[k] = r
            else:
                d[k] = u[k]
    return d

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--conf-file', '-c', type=str, default="stomp.json",
                help="specifies a json configuration file for STOMP to use this run")
    parser.add_argument('--input-trace', '-i', type=str,
                help="specifies the filename from which STOMP should read an input DAG trace")
    parser.add_argument('--conf-json', '-j', type=str,
                help="specifies a json string that includes the configuration information for STOMP to use this run")
    parser.add_argument('--debug', '-d', action="store_true",
                help="Output run-time debugging messages")
    args = parser.parse_args()
    return args

def main(argv):
    args = parse_args()
    conf_file = args.conf_file
    debug = args.debug
    conf_json = args.conf_json
    input_trace_file = args.input_trace

    with open(conf_file) as conf_f:
        stomp_params = json.load(conf_f)
    if conf_json:
        # We update configuration parameters with JSON
        # values received through the command line
        update(stomp_params, json.loads(conf_json))
    if debug:
        stomp_params['general']['logging_level'] = "DEBUG"
    if input_trace_file:
        stomp_params['general']['input_trace_file'] = input_trace_file

    # Dynamically import the scheduling policy class
    sched_policy_module = importlib.import_module(stomp_params['simulation']['sched_policy_module'])

    # Dynamically import the meta policy class
    meta_policy_module = importlib.import_module(stomp_params['simulation']['meta_policy_module'])

    max_timesteps = 2**64
    sharedObjs = SharedObjs(max_timesteps)
    sharedObjs.setup_env()

    stomp_sim = STOMP(sharedObjs, stomp_params, sched_policy_module.SchedulingPolicy())
    meta_sim  = META(sharedObjs, stomp_params, stomp_sim, meta_policy_module.MetaPolicy())

    stomp_sim.meta = meta_sim

    sharedObjs.run()

if __name__ == "__main__":
   main(sys.argv[1:])
