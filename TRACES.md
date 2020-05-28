# STOMP: Scheduling Techniques Optimization in heterogeneous Multi-Processors

STOMP is a simple yet powerful queue-based **discrete-event** simulator that enables fast implementation and evaluation of OS scheduling policies in multi-core/multi-processor systems. It implements a convenient interface to allow users and researchers to _plug in_ new scheduling policies in a simple manner and without the need to touch the STOMP code.

This branch of STOMP introduces support for Directed Acyclic Graph (DAG) processing and scheduling of the tasks that compose each DAG

STOMP supports DAG traces in order to provide the user with the ability to produce a completely re-producible input to a series of STOMP parameter sets.
STOMP can be used to both generate and consume such traces.

## STOMP Input Trace Format
atime,dag_id,dag_type,deadline

The STOMP input trace format consists of a time of arrival, a DAG ID, DAG type, and a deadline per DAG that can be used for real-time scheduling. 

## DAG description format
Describes the DAG structure, i.e. the tasks and their dependencies using a graphml format.

## DAG Task description and timing Profile format
The task type and timing profile for all servers is provided in a txt file present in the inputs folder.
This provides a complete set of information of all tasks in the DAG and how a particular task would execute within the STOMP simulation, and therefore guarantees that subsequent simulations (e.g. with differing numbers of servers, etc.) can produce a representation of the run that is consistent, varying only in the parameterized changes in the STOMP parameters (e.g. the number of servers of each type, the scheduling policy, etc.) and not unintentionally in parameters of the underlying execution (e.g. execution time on a particular server instance).

The Timing Profile format is a simple comma-separated ASCII format which contains the following information:
 * A header row (line) that indicates the ordered set of server_types in the profile
 * One row (line) per task includes 
   * The task type 
   * The server type service time for that task (for each server type)

Each non-header line of the timing file conatins an ASCII entry for a single task, in the form:
   task,s1_time,s2_time,...,sn_time
where task is the task type from the json configuration file (e.g. fft, decoder, etc.)
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

 * Augusto Vega (IBM) --  ajvega@us.ibm.com
 * J-D Wellman (IBM) -- wellman@us.ibm.com

## Current Maintainers

 * Augusto Vega (IBM) --  ajvega@us.ibm.com
 * J-D Wellman (IBM) -- wellman@us.ibm.com
