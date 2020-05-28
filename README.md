# STOMP: Scheduling Techniques Optimization in heterogeneous Multi-Processors 

STOMP is a simple yet powerful queue-based **discrete-event** simulator that enables fast implementation and evaluation of OS scheduling policies in multi-core/multi-processor systems. It implements a convenient interface to allow users and researchers to _plug in_ new scheduling policies in a simple manner and without the need to touch the STOMP code.

STOMP is based on its predecesor C-based <a href="https://ieeexplore.ieee.org/document/5749737" target="_blank">QUTE framework</a>.


## Usage

STOMP is invoked using the `stomp_main.py` script which supports the following options:

 * `-h` or `--help` : Print the usage information
 * `-d` or `--debug` : Output run-time debugging messages
 * `-c` *_S_* or `--conf-file=`*_S_* : Specifies *_S_* as a json configuration file for STOMP to use this run
 * `-j` *_S_* or `--conf-json=`*_S_* : Specifies *_S_* as a json string that includes the configuration information for STOMP to use this run
 * `-i` *_S_* or `--input-trace=`*_S_* : Specifies *_S_* as the filename from which STOMP should read an input task trace


## Traces

STOMP supports a trace-driven operation. STOMP can generate a trace file using the `trace_generator.py`.
Once a trace has been generated, STOMP runs can use that trace in the input trace mode:

 * **Input-trace mode** : this means that the STOMP simulation will faithfully use the task type, arrival time, and service times from the input trace.  This limits the ability of parameter changes (e.g. alterations in the mean service times, or the standard deviation) to affect the run-time behavior, since the task service times are taken from the input trace.  This does allow one to isolate the impact (in some sense) of the scheduling policy on overall performance.


## Requirements

STOMP requires:
 - Python 2.7
 - Python modules
    - numpy
    - networkx


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
