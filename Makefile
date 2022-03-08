
run_syn: simulator/stomp_main.py simulator/stomp.py simulator/meta.py inputs/stomp.json
	./simulator/stomp_main.py

run_ad: simulator/stomp_main.py simulator/stomp.py simulator/meta.py inputs/stomp_real.json
	./simulator/stomp_main.py --conf-file=inputs/stomp_real.json

clean:
	rm sched.* run_stdout_*

clobber:
	rm -r sim_*
