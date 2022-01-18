# STOMP Parameter Sweep Example Script

run_all.py is a simple Python script used to invoke a series of STOMP runs across a sweep of parameters.  In this example, the run_all.py will sweep across a set of different standard deviation factors and scheduling policies, running a STOMP simulation at each point, and then generating some aggregated files summarizing the average response time and queue size during the run.
The results of the run are placed into a directory which is automatically generated, and has the form sim_<date>_<time>.

## USAGE

The general invocation is quite conventional; this script should be invoked from the "stomp" directory level, as:
```
./utils/run_all.py
```

## OPTIONS

The run_all.py script supports both command-line options, and script-modification options.

### Command Line Options
 
 * -h or --help : This outputs the usage information 
 * -s or --save-stdout  : This saves the output of each STOMP run into the file.
 * -u or --user-trace : This indicates that the run_all.py run should use a set of pre-defined user traces.  Currently this uses traces with the name format user_gen_trace_prob_NNN.trc in the stomp/user_traces directory.  These traces are used as input traces (and thus keyed to the probability value, i.e. probability of critical DAGs in the trace) but will dynamically react to the Mean Arrival Time Scaling factor parameter of the STOMP run.  This allows the runs to use consistent task and DAG service times (and scaled DAG arrival trates) across a number of different policies and arrival time scalings.
 * -c or --csv-out : This indicates that the summary output files should be written in CSV (comma separated value) format.
 * -v : This runs the script in a verbose manner

### In-Script Options

The run_all.py script specifies the baseline configuration file, and the set of scheduling policies and standard deviation factors to use in the parametric sweep in a few lines near the top of the file (just after the includes):
```
CONF_FILE    = './stomp.json'
POLICY       = ['simple_policy_ver1', 'simple_policy_ver2', 'simple_policy_ver3', 'simple_policy_ver4', 'simple_policy_ver5', 'edf', 'edf_ver5',  'ads', 'ms1_hom','ms1_hetero','ms1_hyb', 'ms1_hyb_update']
ARRIVE_SCALE = [0.8, 1.0, 1.2, 1.4] 
PROB         = [0.1, 0.2, 0.3, 0.4, 0.5]
```

Altering these values, e.g. by adding or removing entries from the ARRIVE_SCALE list, will cause the run_all.py script to run a modified parametric sweep, but will still generate all the same data, etc. 
__NOTE that altering the POLICY list also requires the addition of new policy files in the policies subdirectory of stomp (by the same name)__

## OUTPUTS

The results of the run are put into an automtically generated directory names sim_<date>_<time>.
This directory will hold a numb er of files:
 * avg_resp_time.out  : This has a summary of the average response time across all the SOTMP simulations
 * queue_size_hist.out : This holds information about the queue size during the run, including some histogram information
 * policy:simple_policy_ver1__stdev_factor:0.01.decoder.simple_policy_ver1.trace : There will be a number of such files, named similarly to this; the name is policy:<policy_name>__stdev_factor:<value>.<task_type>.<policy_name>.trace and it holds a record of all the tasks of type <task_type> simulated during the run.  This file provides information about each task, including origination time, service time, etc. 

## Requirements

STOMP requires:
 * Python 2.7


## Contributors

 * Augusto Vega (IBM) --  ajvega@us.ibm.com
 * J-D Wellman (IBM) -- wellman@us.ibm.com

## Current Maintainers

 * Augusto Vega (IBM) --  ajvega@us.ibm.com
 * J-D Wellman (IBM) -- wellman@us.ibm.com
