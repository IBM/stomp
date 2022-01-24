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

import sys, getopt
import importlib
import json
import simpy
from collections import abc
import threading
from multiprocessing.managers import SyncManager

from stomp import STOMP
from meta import META

import utils
from utils import MyPriorityQueue, EventQueue, CheckableQueue, handle_event

class MyManager(SyncManager):
    pass

def Manager():
    m = MyManager()
    m.start()
    return m

#
# class Global_task_trace(object):
#     def __init__(self):
#         self.queue = []
#     def append(self, item):
#         self.queue.append(item)
#     def sort(self, key, reverse):
#         self.queue.sort(key=key, reverse=reverse)
#     def get(self, ind):
#         return self.queue[ind]
#     def empty(self):
#         return not self.queue
#     def len(self):
#         return len(self.queue)


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

def main(argv):
    MyManager.register("MyPriorityQueue", MyPriorityQueue)  # Register a shared PriorityQueue
    MyManager.register("EventQueue", EventQueue)  # Register a shared EventQueue
    MyManager.register("CheckableQueue", CheckableQueue)  # Register a shared CheckableQueue

    print("[stomp_main] start")
    try:
        opts, args = getopt.getopt(argv,"hdpc:j:i:",["help", "conf-file=", "conf-json=", "debug", "input-trace="])
    except getopt.GetoptError:
        usage_and_exit(2)

    conf_file = "stomp.json"
    conf_json = None
    log_level = None
    input_trace_file = None
    input_trace_external = False

    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage_and_exit(0)
        elif opt in ("-c", "--conf-file"):
            conf_file = arg
        elif opt in ("-j", "--conf-json="):
            conf_json = json.loads(arg)
        elif opt in ("-i", "--input-trace="):
            input_trace_file = arg
            input_trace_external = True
        elif opt in ("-d", "--debug"):
            log_level = "DEBUG"

    with open(conf_file) as conf_file:
        stomp_params = json.load(conf_file)
    if (conf_json):
        # We update configuration parameters with JSON
        # values received through the command line
        update(stomp_params, conf_json)

    # Dynamically import the scheduling policy class
    sched_policy_module = importlib.import_module(stomp_params['simulation']['sched_policy_module'])

    # Dynamically import the meta policy class
    meta_policy_module = importlib.import_module(stomp_params['simulation']['meta_policy_module'])

    if (log_level):
        stomp_params['general']['logging_level'] = log_level

    #print('Setting input_arr_tr file to %s\n' % (input_trace_file))
    if input_trace_external:
        stomp_params['general']['input_trace_file'] = input_trace_file

    # Instantiate and run STOMP, print statistics
    # stomp_sim = STOMP(stomp_params, sched_policy_module.SchedulingPolicy())


    # BaseManager.register('Global_task_trace', Global_task_trace)
    # manager = BaseManager()
    # manager.start()
    # global_task_trace = manager.Global_task_trace()
    # drop_hint_list = manager.Global_task_trace()
    # tasks_completed = manager.Global_task_trace()


    env = simpy.Environment()
    max_timesteps = 2**64
    # max_cap = -1

    m = Manager()
    tsched_eventq      = m.EventQueue() # maxsize=max_cap)
    meta_eventq        = m.EventQueue() # maxsize=max_cap)
    global_task_trace  = m.MyPriorityQueue() # maxsize=max_cap)
    tasks_completed    = m.Queue() # maxsize=max_cap)
    dags_dropped       = m.CheckableQueue() # maxsize=max_cap)
    drop_hint_list     = m.CheckableQueue() # maxsize=max_cap)

    # drop_hint_list = simpy.Resource(env, capacity=max_cap)
    # tasks_completed = simpy.Resource(env, capacity=max_cap)
    # global_task_trace = simpy.PriorityResource(env, capacity=max_cap)

    # tsched_eventq = simpy.PriorityStore(env)
    # meta_eventq = simpy.PriorityStore(env)
    # global_task_trace = simpy.PriorityStore(env)

    # E_META_END = simpy.Store(env, capacity=1)
    task_completed_flag = simpy.Store(env, capacity=1)

    lock = simpy.Resource(env, capacity=1)
    tlock = simpy.Resource(env, capacity=1)
    stomp_sim = STOMP(env, max_timesteps, tsched_eventq, meta_eventq, global_task_trace, tasks_completed, dags_dropped, drop_hint_list, lock, tlock, stomp_params, sched_policy_module.SchedulingPolicy())
    meta_sim = META(env, max_timesteps, tsched_eventq, meta_eventq, global_task_trace, tasks_completed, dags_dropped, drop_hint_list, lock, tlock, stomp_params, stomp_sim, meta_policy_module.MetaPolicy())
    stomp_sim.meta = meta_sim
    stomp_sim.meta_proc = meta_sim.action
    # env.process(meta_sim.run())
    # env.process(stomp_sim.run())

    env.run(until=max_timesteps)
    # thread1 = threading.Thread(target=meta_sim.run)
    # thread2 = threading.Thread(target=env.run, args=(max_timesteps,))
    # env.run()
    # Will execute both in parallel
    # thread1.start()
    # thread2.start()
    #
    # thread1.join()
    # thread2.join()
    # meta_sim.run()
    # stomp_sim.run()


if __name__ == "__main__":
   main(sys.argv[1:])
