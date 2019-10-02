#!/usr/bin/env python
import sys, getopt
import importlib
import json
import collections
import numpy

class TRACE:

    def __init__(self, stomp_params):
        self.params = stomp_params
        self.params['max_dags_simulated'] = 1000
        self.output_trace_file = "user_traces/user_gen_trace_stdf_0.01.trc"
        self.working_dir = "."
        self.sim_time = 0
        self.count_dags = 0

    def run(self):
        if (self.output_trace_file):
            out_trace_name = self.working_dir + '/' + self.output_trace_file
            # logging.info('Generating output trace file to %s' % (out_trace_name))
            output_trace = open(out_trace_name, 'w')


        for dag_id in range(self.params['max_dags_simulated']):
            atime = self.sim_time
            dag_id = self.count_dags
            dag_type = numpy.random.choice(['5','10'])
            priority = numpy.random.choice(['1','2'])
            if dag_type == '5':
                deadline = 800
            else:
                deadline = 1700
            # trace_entry = (atime,dag_id,dag_type,priority,deadline)
            output_trace.write('%d,%d,%s,%s,%d\n' % (atime,dag_id,dag_type,priority,deadline))

            self.sim_time = int(round(self.sim_time + numpy.random.exponential(scale=self.params['simulation']['mean_arrival_time']*self.params['simulation']['arrival_time_scale'], size=1)))
            self.count_dags += 1

if __name__ == "__main__":
   
    conf_file = "stomp.json"   
    stomp_params = {}
    with open(conf_file) as conf_file:
        stomp_params = json.load(conf_file)
    trace = TRACE(stomp_params)
    trace.run()

