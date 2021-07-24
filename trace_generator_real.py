#!/usr/bin/env python
import sys, getopt
import importlib
import json
import collections
import numpy

probs = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
#app = "ad_50"
#dag_type_choice = [0,1,2,3]
#deadline = [400, 400, 400, 400] #ad
#mat = 50


#app = "mapping_25"
#dag_type_choice = [0,1,2]
#deadline = [1536, 167, 1140] #mapping
#mat = 25

app = "package_25"
dag_type_choice = [0,1,2]
deadline = [2144, 167, 1140] #package
mat = 25


class TRACE:

    def __init__(self, stomp_params):
        self.params = stomp_params
        self.params['max_dags_simulated'] = 1000
        self.output_trace_file = ""
        self.working_dir = "."
        self.sim_time = 0
        self.count_dags = 0

    def run(self):

        output_trace = {}
        for prob in probs:
            self.output_trace_file = "input_trace/" + app + "_trace_uniform_" + str(int(prob*100)) + ".trc"
            if (self.output_trace_file):
                out_trace_name = self.working_dir + '/' + self.output_trace_file
                # logging.info('Generating output trace file to %s' % (out_trace_name))
                output_trace[prob] = open(out_trace_name, 'w')

        self.sim_time = 0
        self.count_dags = 0

        print("MAT: %d, ATS: %d" %(mat,self.params['simulation']['arrival_time_scale']))

        for dag_id in range(self.params['max_dags_simulated']):
            atime = self.sim_time
            dag_id = self.count_dags
            dag_type = numpy.random.choice(dag_type_choice)
            for prob in probs:
                if (dag_id % (int(1/prob)) == 0):
                    priority = '3'
                    #priority = numpy.random.choice(['1','3'], p=[1-prob, prob])
                else:
                    priority = '1'
                deadline_dag = deadline[dag_type]
                # trace_entry = (atime,dag_id,dag_type,priority,deadline_dag)
                output_trace[prob].write('%d,%d,%d,%s,%d\n' % (atime,dag_id,dag_type,priority,deadline_dag))

            self.sim_time = int(round(self.sim_time + numpy.random.exponential(scale=mat*self.params['simulation']['arrival_time_scale'], size=1)))
            self.count_dags += 1

if __name__ == "__main__":
   
    conf_file = "stomp2.json"   
    stomp_params = {}
    with open(conf_file) as conf_file:
        stomp_params = json.load(conf_file)
    trace = TRACE(stomp_params)
    trace.run()

