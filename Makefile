
run_syn: simulator/stomp_main.py simulator/stomp.py simulator/meta.py inputs/stomp.json
	python ./simulator/stomp_main.py

run_ad: simulator/stomp_main.py simulator/stomp.py simulator/meta.py inputs/stomp_real.json
	python ./simulator/stomp_main.py --conf-file=inputs/stomp_real.json

run_pm: simulator/stomp_main.py simulator/stomp.py simulator/meta.py inputs/stomp_pm.json
	python ./simulator/stomp_main.py --conf-file=inputs/stomp_pm.json

run_era: simulator/stomp_main.py simulator/stomp.py simulator/meta.py inputs/stomp_era.json
	python ./simulator/stomp_main.py --conf-file=inputs/stomp_era.json

clean:
	rm sched.* run_stdout_*

clobber:
	rm -r sim_*
