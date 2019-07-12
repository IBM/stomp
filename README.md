# STOMP: Scheduling Techniques Optimization in heterogeneous Multi-Processors 

STOMP is a simple yet powerful queue-based **discrete-event** simulator that enables fast implementation and evaluation of OS scheduling policies in multi-core/multi-processor systems. It implements a convenient interface to allow users and researchers to _plug in_ new scheduling policies in a simple manner and without the need to touch the STOMP code.

STOMP is based on its predecesor C-based <a href="https://ieeexplore.ieee.org/document/5749737" target="_blank">QUTE framework</a>.


## Usage

STOMP is invoked using the `stomp_main.py` script which supports the following options:

 * `-h` or `--help` : Print the usage information
 * `-d` or `--debug` : Output run-time debugging messages
 * `-c` *_S_* or `--conf-file=`*_S_* : Specifies *_S_* as a json configuration file for STOMP to use this run
 * `-j` *_S_* or `--conf-json=`*_S_* : Specifies *_S_* as a json string that includes the configuration information for STOMP to use this run
 * `-p` or `--pre-gen-arrivals` : Specifies that STOMP should compute all task types/arrival times before starting the simulation
 * `-g` *_S_* or `--generate-trace=`*_S_* : Specifies *_S_* as the filename into which STOMP will write (generate) a task trace
 * `-i` *_S_* or `--input-trace=`*_S_* : Specifies *_S_* as the filename from which STOMP should read an input task trace
 * `-a` *_S_* or `--arrival-trace=`*_S_* : Specifies *_S_* as the filename from which STOMP should read a task arrival trace


## Traces

STOMP supports both dynamic (i.e. randomly generated task type, arrival, and service time) and trace-driven operational modes.  The dynamic operation further supports in-situ generation (i.e. each task arrival information is generated only as-needed) and a-priori generation (all task arrival information is generated before simulation begins -- this is the pre-gen-arrivals option).  The use of pre-generated (a-priori) task arrivals provides a much more stable/repeatable task stream (for a given random number seed).  
STOMP can automatically generate a trace file from a run (usually conducted in one of the dynamic modes) using the generate-trace option.
Once a trace has been generated, subsequent STOMP runs can use that trace in one of two modes:

 * **Input-trace mode** : this means that the STOMP simulation will faithfully use the task type, arrival time, and service times from the input trace.  This limits the ability of parameter changes (e.g. alterations in the mean service times, or the standard deviation) to affect the run-time behavior, since the task service times are taken from the input trace.  This does allow one to isolate the impact (in some sense) of the scheduling policy on overall performance.
 
 * **Arrival-trace mode** : this means taht the STOMP simulation will take only the task type and arrival time information from the trace, and will produce new server times for this run (_note that this is done a-priori, i.e. at trace read time__).  This mode allows the STOMP run to faithfully reproduce the stream of incoming tasks (and arrival times) but also to react to new STOMP configuration parameters (e.g. mean service times and/or standard deviations).


## Requirements

STOMP requires:
 - Python 2.7


## Running STOMP

STOMP can be configured using the `stomp.json` file. To run it:

```
./stomp_main.py
```


## Contributors and Current Maintainers

 * Augusto Vega (IBM) --  ajvega@us.ibm.com
 * John-David Wellman (IBM) -- wellman@us.ibm.com
 * Aporva Amarnath (IBM) -- aporva.amarnath@ibm.com

## Do You Want to Contribute? Contact Us!

 * Augusto Vega (IBM) --  ajvega@us.ibm.com
 * John-David Wellman (IBM) -- wellman@us.ibm.com
