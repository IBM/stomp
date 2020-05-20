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
        self.output_trace_file = None
        self.working_dir = "."
        self.sim_time = 0
        self.count_dags = 0

    def run(self):

        self.sim_time = 0
        self.count_dags = 0
        self.output_trace_file = "user_traces/user_gen_trace.trc"
        if (self.output_trace_file):
            out_trace_name = self.working_dir + '/' + self.output_trace_file
            # logging.info('Generating output trace file to %s' % (out_trace_name))
            output_trace = open(out_trace_name, 'w')


        output_trace.write('atime,dag_id,dag_type,deadline\n')
        for dag_id in range(self.params['max_dags_simulated']):
            atime = self.sim_time
            dag_id = self.count_dags
            dag_type = numpy.random.choice(['5','7', '10'])
            if dag_type == '5':
                deadline = 537
            elif dag_type == '7':
                deadline = 428
            else:
                deadline = 1012
            output_trace.write('%d,%d,%s,%d\n' % (atime,dag_id,dag_type,deadline))

            self.sim_time = int(round(self.sim_time + numpy.random.exponential(scale=self.params['simulation']['mean_arrival_time']*self.params['simulation']['arrival_time_scale'], size=1)))
            self.count_dags += 1

if __name__ == "__main__":
   
    conf_file = "stomp.json"   
    stomp_params = {}
    with open(conf_file) as conf_file:
        stomp_params = json.load(conf_file)
    trace = TRACE(stomp_params)
    trace.run()

