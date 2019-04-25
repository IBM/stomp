# STOMP: Scheduling Techniques Optimization in heterogeneous Multi-Processors

STOMP is a simple yet powerful queue-based **discrete-event** simulator that enables fast implementation and evaluation of OS scheduling policies in multi-core/multi-processor systems. It implements a convenient interface to allow users and researchers to _plug in_ new scheduling policies in a simple manner and without the need to touch the STOMP code.

STOMP supports task traces in order to provide the user with the ability to both generate specific profiles of task arrival/execution and to produce a completely re-producible input to a series of STOMP parameter sets.
STOMP can be used to both generate and consume such traces.

## STOMP Input Trace Format

The STOMP input trace format consists of a time of arrival, a task type, and an execution time (for that task) per server type.  This provides a complete set of information to determine how a particular task would execute within the STOMP simulation, and therefore guarantees that subsequent simulations (e.g. with differing numbers of servers, etc.) can produce a representation of the run that is consistent, varying only in the parameterized changes in the STOMP parameters (e.g. the number of servers of each type, the scheduling policy, etc.) and not unintentionally in parameters of the underlying execution (e.g. execution time on a particular server instance).

The trace format is a simple comma-separated ASCII format which contains the following information:
 * A header row (line) that indicates the ordered set of server_types in the trace
 * One row (line) per task arrival that includes 
   * The task arrival time
   * The task type 
   * The server type service time for that task (for each server type)

Each non-header line of the trace file conatins an ASCII entry for a single task arrival, in the form:
   time,task,s1_time,s2_time,...,sn_time
Where time is the task arrival time (an integer value)
and task is the task type from the json configuration file (e.g. fft, decoder, etc.)
and s1_time is the execution time for that task on server type 1 (taken from the json file, e.g. cpu_core, gpu, fft_accel, etc.)

### NOTES:
If a given task cannot execute on a given server type, then the service time for that server type should be entered as None.
The ordering of the servers is specified in the first line of the trace file, and all task entries must contain a matching number of service times, whcih are applied to the server types in that order.

## Example trace file
The following illustrates the start of a trace file for a system with 3 server types (cpu_core, gpu, and fft_accel) and two types of arriving tasks (fft, decoder).
```
cpu_core, gpu, fft_accel
0,fft,250,150,50
45,decoder,100,200,None
100,fft,221,160,71
```
This trace illustrates 3 arriving tasks, first an fft at time 0 (with execution times of 250 on cpu_core, 150 on gpu, and 50 on fft_accel) adn then a decoder task at time 45 (with execution times of 100 on cpu_core, 200 on gpu, and no possible execution on an fft_accel server), and then another fft at time 100 (with execution times of 221 on cpu_core, 160 on gpu, and 71 onb fft_accel).  


## Requirements

STOMP requires:
 - Python 2.7


## Contributors

Augusto Vega (IBM) --  ajvega@us.ibm.com
J-D Wellman (IBM) -- wellman@us.ibm.com

## Current Maintainers

Augusto Vega (IBM) --  ajvega@us.ibm.com
J-D Wellman (IBM) -- wellman@us.ibm.com
