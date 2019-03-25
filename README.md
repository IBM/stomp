# STOMP: Scheduling Techniques Optimization in heterogeneous Multi-Processors 

STOMP is a simple yet powerful queue-based **discrete-event** simulator that enables fast implementation and evaluation of OS scheduling policies in multi-core/multi-processor systems. It implements a convenient interface to allow users and researchers to _plug in_ new scheduling policies in a simple manner and without the need to touch the STOMP code.

STOMP is based on its predecesor C-based <a href="https://ieeexplore.ieee.org/document/5749737" target="_blank">QUTE framework</a>.


## Requirements

STOMP requires:
 - Python 2.7


## Running STOMP

STOMP can be configured using the `stomp.json` file. To run it:

```
./stomp_main.py
```

## Contributors

Augusto Vega (IBM) --  ajvega@us.ibm.com


## Current Maintainers

Augusto Vega (IBM) --  ajvega@us.ibm.com
