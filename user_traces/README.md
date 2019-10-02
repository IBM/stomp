# STOMP: USer-Traces

These traces are intended to be used as "user-generated" traces with STOMP, primarily with the --user-trace option of the utile/run_all_2.py script/program.  
These traces were developed by running STOMP and using the --generate-trace option for each StDev Factor run (for one of the policies) and then "massaging" the resulting trace so that the underlying task service times were more "consistent" across the various servers.  One limitation of the original STOMP methodology (still in place) is that each task obtains a separate, uncorrelated value for each server (type) service time, which can lead to some strange results like a given task requiring twenty percent longer than the server type mean service time on one server type and fifty percent shorter than the mean service time on another.  It is expected that the variability will be better correlated than this, since this variability in service time is some kind of measure either of the given current task "size" or "complexity" and this should provide for a correlated timing change (from each mean service time)across the server types. 

These traces currently use "magic" names; the names are formulaic (i.e. they start with "user_gen_trace_stdf_" then have the stander-deviation factor (from the run_all.py script) numeric value, and then ".trc" reulting in a name like 
'''
user_gen_trace_stdf_0.3.trc
'''
which is known to the run_all_2.py script, and expected to be in the user_traces directory.  This can be better generalized in the future.

## Contributors

 * Augusto Vega (IBM) --  ajvega@us.ibm.com
 * John-David Wellman (IBM) -- wellman@us.ibm.com

## Current Maintainers

 * Augusto Vega (IBM) --  ajvega@us.ibm.com
 * John-David Wellman (IBM) -- wellman@us.ibm.com
