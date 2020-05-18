# STOMP Parameter Sweep Example Script

`run_all.py` is a simple Python script used to invoke a series of STOMP runs across a sweep of parameters, and then generating some aggregated files summarizing the average response time and queue size during the run. The results of the run are placed into a directory which is automatically generated, and has the form `sim_<date>_<time>`.

## USAGE

The script is invoked from the `stomp/` directory level as:

```
./utils/run_all.py
```

## OPTIONS

The `run_all.py` script supports both command-line options, and script-modification options.

### Command Line Options
 
 * `-h` or `--help`: Outputs the usage information. 
 * `-s` or `--save-stdout` : Saves the output of each STOMP run into the file.
 * `-p` or `--pre-gen-tasks`: Instructs STOMP to pre-generate the task information (at the start of the run). This results in a consistent set of tasks across the runs; it is effectively a "dynamically-generated" trace.
 * `-a` or `--arrival-trace`: Causes the first run of a STOMP simulation to generate a trace, which will then be used as an arrival trace by every succeeding STOMP simulation run. This guarantees that the task arrival time and task types are consistent across all the STOMP simulations and provides an exact trace of that first simulation (which can be used in future simulations, etc.). Note that the trace is used as an _arrival_ trace and not an "input" trace because the `run_all.py` script alters (scales) the standard deviations across runs, and the input trace fixes the task service times (which the arrival trace does not).
 * `-i` or `--input-trace`: Cause the first run of a STOMP simulation to generate a trace, which will then be used as an _input_ trace by every succeeding STOMP simulation run. This guarantees that the task arrival time and task types are consistent across all the STOMP simulations, as well as the task service times.  This is NOT a useful option when scaling the standard deviation factors.
 * `-u` or `--user-trace`: Indicates that the `run_all_2.py` run should use a set of pre-defined user traces. Currently this uses traces with the name format `user_gen_trace_stdf_NNN.trc` in the `stomp/user_traces/` directory. These traces are used as input traces (and thus keyed to the StDev Factor value, i.e. one trace per StDev Factor) but will dynamically react to the Mean Arrival Time Scaling factor parameter of the STOMP run. This allows the runs to use consistent task service times (and scaled task arrival rates) across a number of different policies and arrival time scalings.

The following option only applies to `run_all_2.py`:

 * `-c` or `--csv-out`: Indicates that the summary output files should be written in CSV (comma separated value) format.


### In-Script Options

The `run_all.py` script specifies the baseline configuration file, and the set of scheduling policies and standard deviation factors to use in the parametric sweep in a few lines near the top of the file (just after the includes):

```
CONF_FILE    = './stomp.json'
POLICY       = ['simple_policy_ver1', 'simple_policy_ver2', 'simple_policy_ver3']
STDEV_FACTOR = [0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]  # percentages
```

Altering these values (e.g. by adding/removing entries to/from the `STDEV_FACTOR` list), will cause the `run_all.py` script to run a modified parametric sweep, but will still generate all the same data, etc. **NOTE that altering the `POLICY` list also requires the addition of corresponding new policy files in the `policies/` subdirectory of STOMP (by the same name)**.


## OUTPUTS

The results of the run are put into an automatically generated directory named `sim_<date>_<time>`.

This directory will hold a number of files:
 * `avg_resp_time.out`: Summary of the average response time across _all_ the STOMP simulations.
 * `queue_size_hist.out`: Information about the queue size during the run, including some histogram information.
 * `policy:simple_policy_ver1__stdev_factor:0.01.decoder.simple_policy_ver1.trace`: There will be a number of such files, following this name format: `policy:<policy_name>__stdev_factor:<value>.<task_type>.<policy_name>.trace`. This file is the temporal trace of all the tasks simulated during the run, including origination time, service time, etc.
