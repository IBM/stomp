#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import pandas as pd
sys.path.append('utils/python-gantt/gantt')
import gantt
import os

start_ts = 0
#end_ts   = -1 #300 # 200
end_ts   = -1 # 200
group_bys = [
    #'server_type_flat',
    # 'server_type',
    # 'criticality',
    None
]

colors = [
        '#e41a1c',
        '#377eb8',
        '#4daf4a',
        '#a6cee3',
        '#1f78b4',
        '#b2df8a'
        ]
server2col = {} # Map of server type to color.

assert len(sys.argv) >= 2, "Insufficient args"
trace_fname = sys.argv[1]
trace_dir = trace_fname.split('/')[0]

assert os.path.exists(trace_fname), "Trace file doesn't exist"
print("Reading trace file: %s" % trace_fname)

df = pd.read_csv(trace_fname)
df.sort_values(['task_dag_id', 'task_arrival_time'], ascending=[True, True], inplace=True)
# Get list of DAG IDs.
df['is_last'] = False
for dag_id in df.task_dag_id.unique():
    df_series = df.loc[df.task_dag_id == dag_id, 'is_last']
    df.loc[df.task_dag_id == dag_id, 'is_last'] = [False] * (df_series.size-1) + [True]
    # df.loc[df.task_dag_id == dag_id].iloc[-1]['is_last'] = True
# print(df)

if end_ts == -1:
    end_ts = df.curr_job_end_time.max() + 2
    print("end_ts set to %u" % end_ts)

# Change font default
gantt.define_font_attributes(fill='black', stroke='black', stroke_width=0, font_family="Arial")

def gen_svg_for_group(group_by):
    # Create a project
    # if group_by == 'server_type_flat':
    #     p1 = gantt.Project(suppress_text=True)
    # else:
    p1 = gantt.Project()

    # Create resources
    res_names = []; res_name2res = {}; dag_task_id2task = {}
    col_idx = 0
    deadlines = {}
    for row in df.itertuples():
        # print(row)
        dag_id = int(row.task_dag_id)
        tid = int(row.task_tid)
        is_last = int(row.is_last)
        # Get task name
        t = "%u.%u" % (dag_id, tid)

        server = row.type
        server_type_id = "%s (%u)" % (row.type, int(row.id))
        criticality = 'C' + str(row.task_priority)
        # Get resource name
        if group_by == 'server_type' or \
            group_by == 'server_type_flat':
            r = server_type_id # Server type (ID).
            name = t + ', ' + criticality
        elif group_by == 'criticality' or group_by == None:
            r = criticality # Criticality.
            name = t + ', ' + server_type_id
        else:
            raise(ValueError)
        if server not in server2col:
            assert col_idx < len(colors), 'Not enough colors!'
            server2col[server] = colors[col_idx]
            col_idx += 1
        if r not in res_names:
            res_names.append(r)
            res_name2res[r] = gantt.Resource(r)

        # DAG deadline abs time.
        if tid == 0:
            deadlines[dag_id] = int(row.dag_dtime)
        # Get start and end time of task.
        a = row.task_arrival_time
        s = row.curr_job_start_time
        e = row.curr_job_end_time
        # Get parent task IDs
        p = str(row.task_parent_ids).split(' ')
        if len(p) == 1 and p[0] == 'nan':
            p = []
        else:
            parent_dag_id = int(row.task_dag_id)
            try:
                p = [dag_task_id2task[str(parent_dag_id) + '.' + parent_tid] for parent_tid in p]
            except:
                print("Error: corrupt row:")
                print(row)
                exit(1)
        # print(p)
        # print("%s: %d:%d" % (t, s, e))
        # arr_task = gantt.Task(fullname=name, name=t, start=a, stop=s, depends_of=p, resources=[res[r]], next_in_line=True)
        if group_by == 'server_type_flat':
            suppress_text=True
            p = []
            arr_task_opacity=0.
        else:
            suppress_text=False
            arr_task_opacity=0.85
        arr_task = gantt.Task(
            fullname=t,
            name=t,
            start=a,
            stop=s,
            depends_of=p,
            resources=[res_name2res[r]],
            next_in_line=True,
            suppress_text=suppress_text,
            opacity=arr_task_opacity
        )
        exe_task = gantt.Task(
            fullname=name,
            name=t,
            start=s,
            stop=e,
            resources=[res_name2res[r]],
            color=server2col[server],
            suppress_text=suppress_text,
            is_last=is_last
        )

        # Add tasks to this project
        p1.add_task(arr_task)
        p1.add_task(exe_task)
        dag_task_id2task[t] = exe_task

    # Draw
    print("Saving .svg files in: " + trace_dir + "/")
    if group_by == 'criticality':
        p1.make_svg_for_resources(filename=trace_dir + '/' + group_by + '_group.svg', start=start_ts, end=end_ts, resources=res_names.sort())
    elif group_by == 'server_type':
        p1.make_svg_for_resources(filename=trace_dir + '/' + group_by + '_group.svg', start=start_ts, end=end_ts, resources=res_names.sort())
    elif group_by == 'server_type_flat':
        p1.make_svg_for_resources(filename=trace_dir + '/' + group_by + '_group.svg', start=start_ts, end=end_ts, resources=res_names.sort(), one_line_for_tasks=True)
    elif group_by == None:
        p1.make_svg_for_tasks(filename=trace_dir + '/' + 'no_group.svg', deadlines=deadlines, start=start_ts, end=end_ts)

for group_by in group_bys:
    print("[INFO] Drawing Gantt chart for group: " + str(group_by))
    gen_svg_for_group(group_by)
