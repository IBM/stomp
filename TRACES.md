# STOMP: Scheduling Techniques Optimization in heterogeneous Multi-Processors

STOMP is a simple yet powerful queue-based **discrete-event** simulator that enables fast implementation and evaluation of OS scheduling policies in multi-core/multi-processor systems. It implements a convenient interface to allow users and researchers to _plug in_ new scheduling policies in a simple manner and without the need to touch the STOMP code.

This branch of STOMP introduces support for Directed Acyclic Graph (DAG) processing and scheduling of the tasks that compose each DAG

STOMP supports DAG traces in order to provide the user with the ability to produce a completely re-producible input to a series of STOMP parameter sets.
STOMP can be used to both generate and consume such traces.

## STOMP Input Trace Format
atime,dag_id,dag_type,deadline

The STOMP input trace format consists of a time of arrival, a DAG ID, DAG type, and a deadline per DAG that can be used for real-time scheduling. 

## Example trace file
```
atime,dag_id,dag_type,deadline
0,0,7,428
89,1,7,428
111,2,7,428
```
## DAG description format
Describes the DAG structure, i.e. the tasks and their dependencies using a graphml format.

## Example DAG file
```
<?xml version='1.0' encoding='utf-8'?>
<graphml xmlns="http://graphml.graphdrawing.org/xmlns" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://graphml.graphdrawing.org/xmlns http://graphml.graphdrawing.org/xmlns/1.0/graphml.xsd">
  <graph edgedefault="directed">
    <node id="0"></node>
    <node id="1"></node>
    <node id="2"></node>
    <edge source="0" target="1" />
    <edge source="1" target="2" />
    <edge source="0" target="2" />
  </graph>
</graphml>
```
where, the DAG consists of three tasks with dependencies between task (0,1), (1,2) and (0,2)

## DAG Task Description and Timing Profile format
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

## Example timing file
The following illustrates the timing profile file for a system with 3 server types (cpu_core, gpu, and fft_accel) and three tasks in a DAG(fft, decoder, fft).
```
cpu_core, gpu, fft_accel
fft,250,150,50
decoder,100,200,None
fft,221,160,71
```
This file illustrates 3 tasks, first an fft (with execution times of 250 on cpu_core, 150 on gpu, and 50 on fft_accel) and hen a decoder task (with execution times of 100 on cpu_core, 200 on gpu, and no possible execution on an fft_accel server), and then another fft (with execution times of 221 on cpu_core, 160 on gpu, and 71 on fft_accel).  


## Requirements

STOMP requires:
 - Python 2.7
 - Python modules
  - numpy
  - networkx


## Contributors

 * Augusto Vega (IBM) --  ajvega@us.ibm.com
 * J-D Wellman (IBM) -- wellman@us.ibm.com

## Current Maintainers

 * Augusto Vega (IBM) --  ajvega@us.ibm.com
 * J-D Wellman (IBM) -- wellman@us.ibm.com
