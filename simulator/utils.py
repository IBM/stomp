#!/usr/bin/env python
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

from queue import PriorityQueue
from queue import Queue
from threading import Lock
from multiprocessing.managers import SyncManager
import simpy

class bcolors:
    HEADER    = '\033[95m'
    OKBLUE    = '\033[94m'
    OKCYAN    = '\033[96m'
    OKGREEN   = '\033[92m'
    WARNING   = '\033[93m'
    FAIL      = '\033[91m'
    ENDC      = '\033[0m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'

class events: # listed in priority order
    META_START      = 0
    TASK_ARRIVAL    = 1
    TASK_COMPLETED  = 2
    SERVER_FINISHED = 3
    SCHEDULE_TASK   = 4
    META_DONE       = 5
    SIM_LIMIT       = 6

class MyPriorityQueue(PriorityQueue):
    def __init__(self):
        PriorityQueue.__init__(self)
        self.counter = 0

    def put(self, priority, item):
        PriorityQueue.put(self, (priority, self.counter, item))
        self.counter += 1

    def peek(self):
        priority, _, item = self.queue[0]
        return priority, item

    def get(self, *args, **kwargs):
        priority, _, item = PriorityQueue.get(self, *args, **kwargs)
        return priority, item

    def __str__(self):
        s = ""
        i = 0
        for priority, item in self.queue:
            s += "({},{}) -> ".format(priority, item)
            if i == 20:
                s += "..."
                break
            i += 1
        s += '\n'
        return s

    def __repr__(self):
        return self.__str__()

class EventQueue(PriorityQueue):
    def __init__(self):
        PriorityQueue.__init__(self)
        self.counter = 0

    def put(self, priority, item):
        PriorityQueue.put(self, (priority, item, self.counter))
        self.counter += 1

    def peek(self):
        priority, item, _ = self.queue[0]
        return priority, item

    def get(self, *args, **kwargs):
        priority, item, _ = PriorityQueue.get(self, *args, **kwargs)
        return priority, item

    def __str__(self):
        s = ""
        i = 0
        for priority, item in self.queue:
            s += "({},{}) -> ".format(priority, item)
            if i == 10:
                s += "..."
                break
            i += 1
        s += '\n'
        return s

    def __repr__(self):
        return self.__str__()

class SharedSet():
    def __init__(self):
        self.mutex = Lock()
        self.set_  = {}

    def contains(self, item):
        with self.mutex:
            return item in self.set_.keys()

    def add(self, item_list):
        with self.mutex:
            for item in item_list:
                self.set_[item] = ""

    def remove(self, item):
        with self.mutex:
            del self.set_[item]

def handle_event(env, q):
    # print("waiting for event, eventq size now:{}".format(q.qsize()))
    tick, event = q.get()
    # print("GOT tick {}, event {}".format(tick, event))

    delta = tick - env.now
    while delta:
        try:
            # print("Timeout for {}".format(delta))
            yield env.timeout(delta)
            delta = 0
        except simpy.Interrupt:
            if not q.empty():
                new_tick, _ = q.peek()
                # print("New event @{}, last event @{}".format(new_tick, tick))
                if new_tick < tick:
                    # push back last event onto event queue
                    q.put(tick, event)
                    # pop new event from event queue
                    tick, event = q.get()
                    delta = tick - env.now
    return tick, event

def message_decode_event(obj, event_name):
    if event_name == events.META_START:
        obj.print("META_START")
    elif event_name == events.META_DONE:
        obj.print("META_DONE")
    elif event_name == events.SCHEDULE_TASK:
        obj.print("SCHEDULE_TASK")
    elif event_name == events.SIM_LIMIT:
        obj.print("SIM_LIMIT")
    elif event_name == events.TASK_ARRIVAL:
        obj.print("TASK_ARRIVAL")
    elif event_name == events.SERVER_FINISHED:
        obj.print("SERVER_FINISHED")
    elif event_name == events.TASK_COMPLETED:
        obj.print("TASK_COMPLETED")
    else:
        raise NotImplementedError

class SharedObjs:
    def __init__(self, max_timesteps):
        self.env = simpy.Environment()
        self.max_timesteps = max_timesteps

        SyncManager.register("MyPriorityQueue", MyPriorityQueue)  # Register a shared PriorityQueue
        SyncManager.register("EventQueue", EventQueue)  # Register a shared EventQueue
        SyncManager.register("SharedSet", SharedSet)  # Register a shared SharedSet
        self.m = SyncManager()
        self.m.start()

    def setup_env(self):
        self.tsched_eventq      = self.m.EventQueue()
        self.meta_eventq        = self.m.EventQueue()
        self.global_task_trace  = self.m.MyPriorityQueue()
        self.tasks_completed    = self.m.Queue()
        self.dags_dropped       = self.m.SharedSet()
        self.drop_hint_list     = self.m.SharedSet()

    def run(self):
        self.env.run(until=self.max_timesteps)
