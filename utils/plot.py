# -*- coding: utf-8 -*-

import matplotlib
import numpy as np
from matplotlib.ticker import FuncFormatter, FormatStrFormatter
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import csv, os
import pandas as pd
import difflib

matplotlib.rcParams['xtick.major.pad']='12'

global curr_choice
curr_choice = ""

### SET ME ###
text = 1
choices = [
    'motiv',
    'edf',
    'tsched',
    'rank_ordering',
    'drop',
    'update',
    'drop_and_update',
    'ad',
    'mapping',
    'packing',
    'hetero',
    'power'
    # 
    # OBSOLETE - DO NOT USE
    # 'packing',
    # 'drop_update',
    # 'update_drop',
    ]
##############

DAG_COUNT = 1000
ARR_TIME  = {"synthetic" : 25,
             "mav" : 25,
             "ad" : 50}
UNITS2SEC  = {"synthetic" : 1e-5,
              "mav" : 1e-3,
              "ad" : 1e-3}

colors_6 = [
    "#f0f9e8",
    "#ccebc5",
    "#a8ddb5",
    "#7bccc4",
    "#43a2ca",
    "#0868ac"
]
matplotlib.style.use('tableau-colorblind10')
cdef = plt.rcParams['axes.prop_cycle'].by_key()['color']
print(cdef)

res_root = "./results"
plot_root = "./"
width = .5

cong_dict = {0.1 : "Rural",
             0.2 : "Semi-\nUrban",
             0.3 : "Urban"}

def gen_label(pol_drop_pair):
    if pol_drop_pair[1]:
        return pol_drop_pair[0] + "_drop"
    else:
        return pol_drop_pair[0] + "_no_drop"
def get_common(Pol_drop):
    string = ""
    for pol_drop in Pol_drop:
        base_policy = gen_label(pol_drop)
        if string == "":
            string = base_policy
        else:
            matcher = difflib.SequenceMatcher(a=string, b=base_policy)
            match = matcher.find_longest_match(0, len(matcher.a), 0, len(matcher.b))
            string = matcher.a[match.a:match.a+match.size]
    if string[0] == '_':
        string = string[1:]
    return string

def get_cand_policies(basepol, Pol):
    ret = []
    for pol in Pol:
        if basepol in pol:
            ret.append(pol)
    return ret

markers=['o', 'x', '*', 'p', 'd', 'o', 'x', '*', 'p', 'd', 'o', 'x', '*', 'p', 'd']

def plot_bar(ax, xlabs, Y, Ylabs, ylabel, bbox, ncol, Y2=None, ylabel2=None):
    global width
    print(Y)
    print(Y2)
    print(Ylabs)
    ax.grid(which='major', axis='y')
    x = np.arange(len(xlabs))
    # print(Y2)
    if len(Y) == 1:
        # if "EDF" in Ylabs[0]:
        #     Ylabs[0] = "EDF"
        ax.bar(x, Y[0], 
            width=width, 
            # color=colors_6[-1], 
            # color=plt.rcParams['axes.prop_cycle'].by_key()['color'][1],
            label=Ylabs[0], 
            edgecolor='black',
            lw=.5)
        if text:
            for i, v in enumerate(Y[0]):
                ax.text(x[i], v,  "%.2f" % v, color='red', fontsize=5, rotation=45)
    else:
        for i in range(len(Y)):
            ax.bar(x + width*(2*i-len(Y)+1)/4, Y[i], 
                width=width/2, 
                # color=colors_6[i], 
                # color=plt.rcParams['axes.prop_cycle'].by_key()['color'][i+1],
                label=Ylabs[i], 
                edgecolor='black',
                lw=.5)
            if text:
                for j, v in enumerate(Y[i]):
                    ax.text(x[j] + width*(2*i-len(Y)+1)/4, v, "%.2f" % v, color='red', fontsize=5, rotation=45)
    if Y2:
        ax2 = ax.twinx()
        if len(Y) == 1:
            ax2.plot(x, Y2[0], 
                # color=plt.rcParams['axes.prop_cycle'].by_key()['color'][1],
                marker=markers[0],
                color="black", 
                ls="None",
                label=Ylabs[0])
            if text:
                for j, v in enumerate(Y2[0]):
                    ax2.text(x[j], v, "%.2f" % v, color='red', fontsize=5)
            ax2.set_ylabel(ylabel2)
        else:
            for i in range(len(Y)):
                ax2.plot(x + width*(2*i-len(Y)+1)/4, Y2[i], 
                    # color=plt.rcParams['axes.prop_cycle'].by_key()['color'][i+len(Ylabs)],
                    color="black", 
                    ls="None",
                    marker=markers[i],
                    ms=4,
                    label=Ylabs[i])
                if text:
                    for j, v in enumerate(Y2[i]):
                        ax2.text(x[j] + width*(2*i-len(Y)+1)/4, v, "%.2f" % v, color='red', fontsize=5)
                ax2.set_ylabel(ylabel2)
        # ax2.yaxis.set_major_formatter(FuncFormatter(lambda y, _: '{:g}'.format(y)))
        ax2.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))

    # ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    # ax.set_ylim((0, 3.5))
    ax.set_axisbelow(True)
    ax.set_xticks(x)
    ax.set_xticklabels(xlabs, va='center') #, rotation=45)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: '{:g}'.format(y)))

def plot_bar2(ax, xlabs, Y, Ylabs, ylabel, bbox, ncol, Y2=None, ylabel2=None):
    mplier = 1e3 * UNITS2SEC[workload]  # milliseconds
    ax.grid(which='major', axis='y')
    x = np.arange(len(xlabs))
    Y = [y * mplier for y in Y]
    for i in range(len(Y)):
        ax.bar(x + width*(2*i-len(Y)+1)/4, Y[i], 
            width=width/2, 
            # color=colors_6[i], 
            # color=plt.rcParams['axes.prop_cycle'].by_key()['color'][i+1],
            label=Ylabs[i], 
            edgecolor='black',
            lw=.5)
        if text:
            for j, v in enumerate(Y[i]):
                ax.text(x[j] + width*(2*i-len(Y)+1)/4, v, "%.2f" % v, color='red', fontsize=5, rotation=45)
    ax.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))

    # ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    # ax.set_ylim((0, 3.5))
    ax.set_axisbelow(True)
    ax.set_xticks(x)
    ax.set_xticklabels(xlabs, va='center') #, rotation=45)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: '{:g}'.format(y)))

# def plot_bar2(ax, xlabs, Y, Ylabs, xlabel, ylabel, ncol):
#     # print(Y)
#     # print(Ylabs)
#     Y_ = []
#     Ylabs_ = []
#     for i in range(len(Y)):
#         if Y[i]:
#             Ylabs_.append(Ylabs[i])
#             Y__ = []
#             # print("Y[%u]: %s" % (i, Y[i]))
#             if Y[i]:
#                 for j in range(len(Y[i])):
#                     Y[i][j] *= 100.
#                     # print(Y[i][j])
#                     Y__.append(Y[i][j])
#                 # print(Y__)
#                 Y_.append(Y__)
#     Y = Y_
#     Ylabs = Ylabs_
#     print(Y)
#     print(Ylabs)
#     assert len(Y) == len(Ylabs)
#     assert len(Y[-1]) == len(xlabs)
#     ax.grid(which='major', axis='y')
#     x = np.arange(len(xlabs))
#     # if len(Y) == 2:
#     #     c = [colors_6[2], colors_6[5]]
#     # elif len(Y) == 4:
#     #     c = [colors_6[1], colors_6[2], colors_6[3], colors_6[5]]
#     # else:
#     #     print("Out of colors, need %d" % len(Y))
#     #     exit(1)
#     w = width/3
#     if len(Y) == 1:
#         ax.bar(x, Y[0], 
#             width=w, 
#             # color=colors_6[-1], 
#             label=Ylabs[0], 
#             edgecolor='black',
#             lw=.5)
#     else:
#         for i in range(len(Y)):
#             # x - 3/2 w, x - 1/2 w, x + 1/2 w, x + 3/2 w.
#             ax.bar(x + w*(2*i-len(Y)+1)/2, Y[i], 
#                 width=w, 
#                 # color=colors_6[i], 
#                 label=Ylabs[i], 
#                 edgecolor='black',
#                 lw=.5)

#     ax.set_xlabel(xlabel)
#     ax.set_ylabel(ylabel)
#     ax.set_axisbelow(True)
#     ax.set_xticks(x)
#     ax.set_xticklabels(xlabs, rotation=45)
#     ax.set_ylim((0, 115))
#     # ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: '{:g}'.format(y)))

def main(fsize, path, Pol, Prob, basePol, competingPol, Drop, bbox, ncol, Ylabs, fname=None):
    data = pd.read_csv(path)

    print("Probabilities = " + str(Prob))
    print("Policies = " + str(Pol))
    print("Drop Values = " + str(Drop))

    x = Prob
    print(data.columns)
    # with pd.option_context('display.max_rows', None, 'display.max_columns', None):
    #     print (data_pr2met)

    ################## MISSION SPEEDUP PLOT ######################
    # Pols * Probs * Drops matrix of mission times.
    mis_time = np.zeros((len(Pol), len(Prob), len(Drop)))
    dags_per_s = np.zeros((len(Pol), len(Prob), len(Drop)))
    for i, pol in enumerate(Pol):
        # print("Parsing policy: " + pol)
        for j, prob in enumerate(Prob):
            # print("\tParsing probability: " + str(prob))
            for k, drop in enumerate(Drop):
                data_trim = data[(data["Pr2 Met"] == 1) &
                                 (data["Policy"] == pol) &
                                 (data["PROB"] == prob) &
                                 (data.DROP == drop)]
                if data_trim.empty:
                    continue
                # Select the row with the smallest arrival scale.
                data_trim = data_trim[data_trim["Mission time"] == data_trim["Mission time"].min()]
                curr_arr_scale = data_trim.ARR_SCALE.values
                assert len(curr_arr_scale) == 1, data_trim
                curr_arr_scale = curr_arr_scale[0]
                curr_dags_processed = data_trim["Pr2 Cnt"].values
                assert len(curr_dags_processed) == 1
                curr_dags_processed = curr_dags_processed[0]
                # print("\t\tParsing drop: " + str(drop))
                cur_mis_time = data_trim["Mission time"].values
                # print(cur_mis_time)
                if len(cur_mis_time) != 0:
                    # print('i=%u, j=%u, k=%u' % (i, j, k))
                    # print(data_trim[data_trim.DROP == drop]["Mission time"].values[0])
                    assert len(cur_mis_time) == 1
                    mis_time[i][j][k] = cur_mis_time[0]
                else:
                    print("Prob, Pol, Drop: %s had 0 mission time" % str((prob, pol, drop)))
                    assert False

                curr_resp_time = (mis_time[i][j][k] - curr_arr_scale * ARR_TIME[workload] * DAG_COUNT) * UNITS2SEC[workload]
                cur_dags_per_s = curr_dags_processed / curr_resp_time
                dags_per_s[i][j][k] = cur_dags_per_s

    print("Mission times: " + str(mis_time))
    print("DAGs per second: " + str(dags_per_s))
    # Calculate speedups from mission times.
    # speedups = [time(baseline) / time(pol) for pol in Pol]
    # if len(basePol) == 1 or type(basePol) is tuple:
    #     Y = mis_time[Pol.index(basePol[0]),:,Drop.index(basePol[1])]
    #     base_policy = gen_label(basePol)
    #     print("Baseline policy = " + base_policy + ", baseline mission time per congestion value = " + str(Y))
    #     speedups = []; Ylabs = []
    #     for i, pol in enumerate(Pol):
    #         for k, drop in enumerate(Drop):
    #             if not mis_time[i,:,k].any() \
    #                 or (pol == basePol[0] and drop == basePol[1]): # No data or is baseline.
    #                 # print("Skipping policy %s" % gen_label((pol, drop)))
    #                 continue
    #             speedups.append(np.divide(Y, mis_time[i,:,k]))
    #             Ylabs.append(gen_label((pol, drop)))
    #             print("%s" % Ylabs[-1])
    #             print(speedups[-1])
    #     # Hack to remove _drop.
    #     if len(Drop) == 1 and Drop[0] == False:
    #         Ylabs = [ylab.split('_no_drop')[0] for ylab in Ylabs]
    #         base_policy = base_policy.split('_no_drop')[0]
    #     plot_bar(
    #         fsize,
    #         path.split('/')[-1].split('.csv')[0] + "_0",
    #         [cong_dict[x_] for x_ in x], 
    #         speedups, 
    #         Ylabs, 
    #         "Congestion", 
    #         "Mission Speedup\nover " + base_policy,
    #         ncol
    #     )
    # else:
    dags_per_s_inc = []
    speedups = []; times = []
    # Ylabs = []
    mis_cmpltd_base = []
    for i, basepol in enumerate(basePol):
        mis_cmpltd_base_for_pol = []

        base_mis_time = mis_time[Pol.index(basepol[0]),:,Drop.index(basepol[1])]
        base_dags_per_s = dags_per_s[Pol.index(basepol[0]),:,Drop.index(basepol[1])]
        base_policy = gen_label(basepol)
        if fname == "motiv" and not len(times):
            assert len(basePol) == 1
            times.append(base_mis_time)

        ############## SPEEDUP AND DAG PROC. ##############
        print("Baseline policy:     " + base_policy + ", baseline mission time per congestion value = " + str(base_mis_time))
        # Each policy is only compared to itself here.
        print("Competing with base: " + str(gen_label(competingPol[i])))
        comp_pol = competingPol[i][0]
        comp_drop = competingPol[i][1]
        j = Pol.index(comp_pol)   # pol
        k = Drop.index(comp_drop)   # drop
        print("  Extracting mission time[%u,:,%u] for %s" % (j, k, gen_label(competingPol[i])))
        comp_mis_time = mis_time[j,:,k]
        assert comp_mis_time.any()
        speedups.append(np.divide(base_mis_time, comp_mis_time).tolist())
        if fname == "motiv":
            times.append(comp_mis_time)
        # Ylabs.append(gen_label((comp_pol, comp_drop)))

        print("Speedups of %s over %s: %s" % (comp_pol, base_policy, str(speedups)))

        ############## MISSION COMPLETED AT COMPETING POLICY'S BEST ARR_SCALE ##############
        for j, prob in enumerate(Prob):
            data_trim = data[(data["Pr2 Met"] == 1) &
                             (data["Policy"] == comp_pol) &
                             (data.PROB == prob) &
                             (data.DROP == comp_drop)]
            data_trim = data_trim[(data_trim["Mission time"] == data_trim["Mission time"].min())]

            # print(data_trim)
            comp_best_arr_scale = data_trim.ARR_SCALE.values
            assert len(comp_best_arr_scale) == 1
            # print(comp_best_arr_scale[0])
            # print(data[
            #          (data["Policy"] == basepol[0]) &
            #          (data.ARR_SCALE == comp_best_arr_scale[0]) &
            #          (data.PROB.isin(Prob)) &
            #          (data.DROP == basepol[1])])
            data_trim = data[(data["Policy"] == basepol[0]) &
                             (data.PROB == prob) &
                             (data.DROP == basepol[1])]

            if comp_best_arr_scale[0] not in data_trim.ARR_SCALE.values:
                print("[ERROR] baseline policy \"" + base_policy + 
                    "\" doesn't have data for ARR_SCALE == " + str(comp_best_arr_scale[0]) + 
                    ", PROB == " + str(prob))
                exit(1)
                # continue
            data_trim = data_trim[(data_trim.ARR_SCALE == comp_best_arr_scale[0])]["Mission Completed"]
            # print(data_trim)
            # exit(1)
            assert len(data_trim.values) == 1
            mis_cmpltd_base_for_pol.append(100. * data_trim.values[0])
        mis_cmpltd_base.append(mis_cmpltd_base_for_pol)
        print(">> Frac mis_completed for %s at fastest arrival scale of %s (%s): %s" % 
            (base_policy, comp_best_arr_scale[0], comp_pol, str(mis_cmpltd_base)))

        comp_dags_per_s = dags_per_s[Pol.index(comp_pol),:,Drop.index(comp_drop)]
        print(">> competing dags/ms: " + str(comp_dags_per_s))
        print(">> baseline dags/ms: " + str(base_dags_per_s))
        dags_per_s_inc.append(np.divide(comp_dags_per_s, base_dags_per_s).tolist())

        print(">> Increase in DAGs processed / ms for %s: %s" % (Ylabs[-1], str(dags_per_s_inc)))

    print("dags_per_s_inc: %s\nspeedups: %s\nYlabs: %s\nmis_cmpltd_base: %s"
        % (dags_per_s_inc, speedups, Ylabs, mis_cmpltd_base))
    fn = path.split('/')[-1].split('.csv')[0]
    name = fn.split('/')[-1]
    if name == "hetero":
        fig, ax = plt.subplots(1, 1, figsize=fsize, dpi=300)
    else:
        fig, ax = plt.subplots(1, 2, figsize=fsize, dpi=300)
    plt.minorticks_on()
    plt.tick_params(axis='x', which='minor', bottom=False)

    lab_ext = get_common(basePol)
    # print(lab_ext)
    # Hack for plot.
    # if name == "tsched":
    #     lab_ext = "of AVSched"
    #     lab_ext2 = ""
    if name == "edf" or name == "tsched" or name == "rank_ordering" or name == "motiv":
        Ylabs = [y.split('_no_drop')[0] for y in Ylabs]
        lab_ext2 = "for " + lab_ext.split('_no_drop')[0]
        lab_ext = "over " + lab_ext.split('_no_drop')[0]
    elif name == "ad" or name == "packing" or name == "mapping":
        lab_ext = "of AVSched over baseline"
        lab_ext2 = ""
    elif name == "rank_update" or name == "rank_update1":
        lab_ext = "over no_update"
        lab_ext2 = "for no_update"
    elif fname == "update" or fname == "drop" or fname == "drop_and_update":
        lab_ext = "over MS-NoOpt"
        lab_ext2 = "for MS-NoOpt"
    elif name == "hetero":
        lab_ext = "over RT"
    else:
        lab_ext = "over " + lab_ext
        lab_ext2 = "for " + lab_ext

    # logfile = open("out.csv", 'a')
    # logfile.write(choice + ",")
    # logfile.write(str(speedups) + ",")
    # logfile.write(str(dags_per_s_inc) + ",")
    # logfile.write(str(mis_cmpltd_base) + "\n")
    # logfile.close()

    if name == "hetero":
        plot_bar(
            ax,
            [cong_dict[x_] for x_ in x], 
            speedups, 
            Ylabs, 
            # "Congestion", 
            "Mission Speedup\n" + lab_ext,
            bbox,
            ncol,
        )
    else:
        if fname == "motiv":
            axisLab = "Mission Time (ms)"
            plot_bar2(
                ax[0],
                [cong_dict[x_] for x_ in x], 
                times, 
                [basePol[0][0], competingPol[0][0]], 
                # "Congestion", 
                axisLab,
                bbox,
                ncol
            )
            lab_ext2 = "for RT"
        elif name == "tsched":
            axisLab = "Relative Mission Time"
            plot_bar(
                ax[0],
                [cong_dict[x_] for x_ in x], 
                speedups, 
                Ylabs, 
                # "Congestion", 
                axisLab,
                bbox,
                ncol,
                dags_per_s_inc,
                "Relative Crit. DAG Thpt"
            )
        else:
            axisLab = "Mission Speedup\n" + lab_ext
            plot_bar(
                ax[0],
                [cong_dict[x_] for x_ in x], 
                speedups, 
                Ylabs, 
                # "Congestion", 
                axisLab,
                bbox,
                ncol,
                dags_per_s_inc,
                "Crit. DAG Thpt x\n" + lab_ext,
            )
        # "Congestion", 
        if name == "ad" or name == "mapping" or name == "packing" or name == "tsched":
            lab = " % Mission Completed\n for baseline"
        else:
            lab = " % Mission Completed\n" + lab_ext2
        plot_bar(
            ax[1],
            [cong_dict[x_] for x_ in x], 
            mis_cmpltd_base, 
            Ylabs,
            lab,
            bbox,
            ncol
        )
    # plt.legend(loc="lower center",
    #            prop={'size': 7},
    #            columnspacing=0.45,
    #            bbox_to_anchor=bbox,
    #            ncol=ncol)
    plt.tight_layout(pad=2.)
    if fname:
        fn = fname
    plt.savefig(plot_root + "/" + fn + ".pdf")
    print("Saved figure to: " + plot_root + "/" + fn + ".pdf")



    ################## % MISSION COMPLETED PLOT ######################
    # if len(basePol) == 1 or type(basePol) is tuple:
    #     arr_scales_for_min_mis_time = []; pols_for_min_mis_time = [] # length = len(Prob)
    #     for i, prob in enumerate(Prob):
    #         min_mis_time_for_prob = float("inf")
    #         for j, pol in enumerate(Pol):
    #             for k, drop in enumerate(Drop):
    #                 data_trim = data[(data["Pr2 Met"] == 1) &
    #                                  (data.PROB == prob) &
    #                                  (data.Policy == pol) & 
    #                                  (data.DROP == drop)]
    #                 data_trim = data_trim[data_trim["Mission time"] == 
    #                     data_trim["Mission time"].min()]
    #                 if data_trim.empty:
    #                     continue
    #                 # print("Prev min: " + str(min_mis_time_for_prob))
    #                 if min_mis_time_for_prob > data_trim["Mission time"].values[0]:
    #                     min_mis_time_for_prob = data_trim["Mission time"].values[0]
    #                     # print("New min: " + str(min_mis_time_for_prob))
    #                     arr_scale_for_min_mis_time = data_trim.ARR_SCALE.values[0]
    #                     pol_for_min_mis_time = gen_label((pol,drop))
    #         arr_scales_for_min_mis_time.append(arr_scale_for_min_mis_time)
    #         pols_for_min_mis_time.append(pol_for_min_mis_time)
    #     print(list(zip(arr_scales_for_min_mis_time, pols_for_min_mis_time)))
    #     mis_completed = []
    #     Ylabs = []
    #     for j, pol in enumerate(Pol):
    #         for k, drop in enumerate(Drop):
    #             Ylabs.append(gen_label((pol, drop)))
    #             y = []
    #             # print("Parsing policy: " + Ylabs[-1])
    #             for i, prob in enumerate(Prob):
    #                 # print("\tParsing probability: " + str(prob))
    #                 print(arr_scales_for_min_mis_time[i], pols_for_min_mis_time[i])
    #                 d = data[(data.DROP == drop) & (data.PROB == prob) & 
    #                          (data.Policy == pol) &
    #                          (data.ARR_SCALE == arr_scales_for_min_mis_time[i])]["Mission Completed"]
    #                 if not d.empty:
    #                     y.append(d.values[0])
    #             mis_completed.append(y)
    # else:
        # mis_completed = []
        # Ylabs = []
        # for basepol in basePol:
        #     arr_scales_for_min_mis_time = []; pols_for_min_mis_time = [] # length = len(Prob)
        #     for i, prob in enumerate(Prob):
        #         min_mis_time_for_prob = float("inf")
        #         for j, pol in enumerate(get_cand_policies(basepol[0], Pol)):  # Only compare w/ itself w/ diff drop.
        #             for k, drop in enumerate(Drop):
        #                 data_trim = data[(data["Pr2 Met"] == 1) &
        #                                  (data.PROB == prob) &
        #                                  (data.Policy == pol) & 
        #                                  (data.DROP == drop)]
        #                 data_trim = data_trim[data_trim["Mission time"] == 
        #                     data_trim["Mission time"].min()]
        #                 print(data_trim)
        #                 print(int(data_trim["Mission time"].values[0]))
        #                 # print("Prev min: " + str(min_mis_time_for_prob))
        #                 if float(min_mis_time_for_prob) > float(data_trim["Mission time"].values[0]):
        #                     min_mis_time_for_prob = data_trim["Mission time"].values[0]
        #                     # print("New min: " + str(min_mis_time_for_prob))
        #                     arr_scale_for_min_mis_time = data_trim.ARR_SCALE.values[0]
        #                     pol_for_min_mis_time = gen_label((pol,drop))
        #         arr_scales_for_min_mis_time.append(arr_scale_for_min_mis_time)
        #         pols_for_min_mis_time.append(pol_for_min_mis_time)
        #     # print(list(zip(arr_scales_for_min_mis_time, pols_for_min_mis_time)))
        #     for j, pol in enumerate(get_cand_policies(basepol[0], Pol)):  # Only compare w/ itself w/ diff drop.
        #         for k, drop in enumerate(Drop):
        #             Ylabs.append(gen_label((pol, drop)))
        #             y = []
        #             # print("Parsing policy: " + Ylabs[-1])
        #             for i, prob in enumerate(Prob):
        #                 # print("\tParsing probability: " + str(prob))
        #                 # print(arr_scales_for_min_mis_time[i], pols_for_min_mis_time[i])
        #                 mis_completed_curr = data[(data.DROP == drop) & 
        #                                           (data.PROB == prob) & 
        #                                           (data.Policy == pol) &
        #                                           (data.ARR_SCALE == arr_scales_for_min_mis_time[i])]["Mission Completed"]
        #                 # print(mis_completed_curr.values)
        #                 mis_completed_curr = mis_completed_curr.values[0]
        #                 y.append(mis_completed_curr)
        #             mis_completed.append(y)
        #     # print(Ylabs)
        #     # print(mis_completed)

def plot_power(fsize, path, Prob, bbox, ncol, Xlabs, Ylabs, fname=None):
    x = Prob
    data = pd.read_csv(path)

    E = []; S = []
    for prob in Prob:
        E.append(data[data.Prob == prob].Energy.tolist())
        S.append(data[data.Prob == prob]["Pr2 Slack"].tolist())
        S[-1] = [s * 100. for s in S[-1]]

    fig, ax = plt.subplots(figsize=fsize, dpi=300)
    plt.minorticks_on()
    plt.tick_params(axis='x', which='minor', bottom=False)
    print(E, S) 
    # xlabs = [cong_dict[x_] for x_ in x]
    print(Xlabs) 

    # logfile = open("out.csv", 'a')
    # logfile.write(choice + ",")
    # logfile.write(str(E) + ",")
    # logfile.write(str(S) + ",")
    # logfile.close()

    ax.grid(which='major', axis='y')
    x = np.arange(len(Xlabs))
    ax2 = ax.twinx()
    for i in range(len(E)):
        if i == 0:
            l = Ylabs[0]
        else:
            l = None
        ax.bar(x + width*(3*(i)-len(E)-1.75+1)/4, E[i], 
            width=width/4, 
            # color=colors_6[i], 
            # color=plt.rcParams['axes.prop_cycle'].by_key()['color'][i+1],
            label=l, 
            edgecolor='black',
            color=cdef[0],
            lw=.5)
        if text:
            for j, v in enumerate(E[i]):
                ax2.text(x[j] + width*(3*(i)-len(E)-1.75+1)/4, v, "%.2f" % v, color='red', fontsize=5)
        if i == 0:
            l = Ylabs[1]
        else:
            l = None
        ax2.bar(x + width*(3*(i+0.5)-len(S)-1.75+1)/4, S[i], 
            width=width/4, 
            # color=colors_6[i], 
            # color=plt.rcParams['axes.prop_cycle'].by_key()['color'][i+1],
            label=l, 
            edgecolor='black',
            color=cdef[1],
            lw=.5)
        if text:
            for j, v in enumerate(S[i]):
                ax2.text(x[j] + width*(3*(i+0.5)-len(S)-1.75+1)/4, v, "%.2f" % v, color='red', fontsize=5)
        ax2.yaxis.set_major_formatter(FormatStrFormatter('%.2f'))

    # ax.set_xlabel(xlabel)
    ax.set_ylabel("Relative Energy")
    ax2.set_ylabel("% Slack")
    # ax.set_ylim((0, 3.5))
    ax.set_axisbelow(True)
    ax.set_xticks(x)
    ax.set_xticklabels(Xlabs, va="center") #, rotation=45)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda y, _: '{:g}'.format(y)))
    ax2.set_ylim((0, 100))

    ax.legend(
               loc="lower center",
               prop={'size': 7},
               columnspacing=0.45,
               bbox_to_anchor=(0.4,1),
               ncol=ncol)
    ax2.legend(
               loc="lower center",
               prop={'size': 7},
               columnspacing=0.45,
               bbox_to_anchor=(0.6,1),
               ncol=ncol)
    plt.tight_layout()
    if fname:
        fn = fname
    plt.savefig(plot_root + "/" + fn + ".pdf")
    print("Saved figure to: " + plot_root + "/" + fn + ".pdf")

fsize = (6,2.5)
if __name__ == "__main__":
    for choice in choices:
        curr_choice = choice
        if choice == "power":
            plot_power(
                 fsize=fsize,
                 Prob=[0.1, 0.2, 0.3],
                 path=res_root + "/power.csv",
                 bbox=(.5, 1.1),
                 ncol=4,
                 Ylabs=["Energy", "Slack"],
                 Xlabs=["ADSuite", "3D Mapping", "Package Delivery"],
                 fname="power"
                )
        if choice == "motiv":
            workload = "synthetic"
            main(
                 fsize=fsize,
                 path=res_root + "/motiv.csv",
                 Pol=["2step_EDF", "AVSched"],
                 Prob=[0.1, 0.2, 0.3],
                 basePol=[
                          ("2step_EDF", False),
                         ],
                 competingPol=[
                               ("AVSched", True)
                              ],
                 Drop=[True, False],
                 bbox=(.5, 1.1),
                 ncol=4,
                 Ylabs=["AVSched"],
                 fname="motiv")
        # if "edf" in choices:
        #     workload = "synthetic"
        #     main(
        #          fsize=(5,2.75),
        #          path=res_root + "/edf.csv",
        #          Pol=["EDF", "2step_EDF"],
        #          Prob=[0.1, 0.2, 0.3],
        #          basePol=[("EDF", False)],
        #          competingPol=[("2step_EDF", False)],
        #          Drop=[False],
        #          bbox=(0.5, .9),
        #          ncol=4)
        if choice == "tsched":
            fsize = (5,2.5)
            workload = "synthetic"
            main(
                 fsize=fsize,
                 path=res_root + "/tsched.csv",
                 Pol=["TS1", "TS2"],
                 Prob=[0.1, 0.2, 0.3],
                 basePol=[("TS1", False), ("TS1", False)],
                 competingPol=[("TS1", False), ("TS2", False)],
                 Drop=[False],
                 bbox=(0.5, 1),
                 Ylabs=["TS1", "TS2"],
                 ncol=4)
        if choice == "rank_ordering":
            workload = "synthetic"
            main(
                 fsize=fsize,
                 path=res_root + "/rank_ordering.csv",
                 Pol=["TS2", "MS1", "MS2"],
                 Prob=[0.1, 0.2, 0.3],
                 basePol=[("TS2", False),("TS2", False),("TS2", False)],
                 competingPol=[("MS1", False),("MS2", False)],
                 Drop=[False],
                 bbox=(0.5, 1),
                 Ylabs=["MS1", "MS2"],
                 ncol=4)
        # if "drop" in choices:
        #     workload = "synthetic"
        #     main(
        #          fsize=(5,2.75),
        #          path=res_root + "/dropping.csv",
        #          Pol=["MS1", "MS2"],
        #          Prob=[0.1, 0.2, 0.3],
        #          basePol=[("MS1", False),
        #                   ("MS2", False)],
        #          competingPol=[("MS1", True),
        #                        ("MS2", True)],
        #          Drop=[True, False],
        #          Ylabs=["MS1", "MS2"],
        #          bbox=(0.5, 1),
        #          ncol=3)
        # if "update_drop" in choices:
        #     workload = "synthetic"
        #     main(
        #          fsize=(5,2.75),
        #          path=res_root + "/dropping1.csv",
        #          Pol=["MS1_Update", "MS2_Update"],
        #          Prob=[0.1, 0.2, 0.3],
        #          basePol=[("MS1_Update", False),
        #                   ("MS2_Update", False)],
        #          competingPol=[("MS1_Update", True),
        #                        ("MS2_Update", True)],
        #          Drop=[True, False],
        #          Ylabs=["MS1", "MS2"],
        #          bbox=(0.5, 1),
        #          ncol=3)
        if choice == "drop":
            workload = "synthetic"
            main(
                 fsize=fsize,
                 path=res_root + "/drop_and_update.csv",
                 Pol=[
                      "MS1",
                      "MS2",
                     ],
                 Prob=[0.1, 0.2, 0.3],
                 basePol=[
                          ("MS1", False),
                          ("MS2", False)
                         ],
                 competingPol=[
                               ("MS1", True),
                               ("MS2", True),
                               ],
                 Drop=[True, False],
                 Ylabs=[
                        "MS1_Drop", 
                        "MS2_Drop", 
                       ],
                 bbox=(0.5, 1),
                 ncol=3,
                 fname="drop"
                )
        if choice == "update":
            workload = "synthetic"
            main(
                 fsize=fsize,
                 path=res_root + "/drop_and_update.csv",
                 Pol=[
                      "MS1",
                      "MS2",
                      "MS1_Update", 
                      "MS2_Update", 
                     ],
                 Prob=[0.1, 0.2, 0.3],
                 basePol=[
                          ("MS1", False),
                          ("MS2", False)
                         ],
                 competingPol=[
                               ("MS1_Update", False),
                               ("MS2_Update", False),
                               ],
                 Drop=[False],
                 Ylabs=[
                        "MS1_Update", 
                        "MS2_Update", 
                       ],
                 bbox=(0.5, 1),
                 ncol=3,
                 fname="update"
                 )
        if choice == "drop_and_update":
            workload = "synthetic"
            main(
                 fsize=fsize,
                 path=res_root + "/drop_and_update.csv",
                 Pol=[
                      "MS1_Update",
                      "MS2_Update",
                      "MS1",
                      "MS2",
                     ],
                 Prob=[0.1, 0.2, 0.3],
                 basePol=[
                          ("MS1", False),
                          ("MS2", False)
                         ],
                 competingPol=[
                               ("MS1_Update", True),
                               ("MS2_Update", True),
                               ],
                 Drop=[True, False],
                 Ylabs=[
                        "MS1_Drop_Update", 
                        "MS2_Drop_Update", 
                       ],
                 bbox=(1, 1),
                 ncol=3,
                 fname="drop_and_update"
                 )
        # if "update" in choices:
        #     workload = "synthetic"
        #     main(
        #          fsize=(5,2.75),
        #          path=res_root + "/rank_update1.csv",
        #          Pol=["MS1", "MS2", "MS1_Update", "MS2_Update"],
        #          Prob=[0.1, 0.2, 0.3],
        #          basePol=[("MS1", False),
        #                   ("MS2", False)],
        #          competingPol=[("MS1_Update", False),
        #                        ("MS2_Update", False),
        #          Drop=[False],
        #          bbox=(0.5, 1),
        #          Ylabs=["MS1", "MS2"],
        #          ncol=3)
        # if "drop_update" in choices:
        #     workload = "synthetic"
        #     main(
        #          fsize=(5,2.75),
        #          path=res_root + "/rank_update.csv",
        #          Pol=["MS1", "MS2", "MS1_Update", "MS2_Update"],
        #          Prob=[0.1, 0.2, 0.3],
        #          basePol=[("MS1", True),
        #                   ("MS2", True),
        #          competingPol=[("MS1_Update", True),
        #                        ("MS2_Update", True),
        #          Drop=[True],
        #          bbox=(0.5, 1),
        #          Ylabs=["MS1", "MS2"],
        #          ncol=3)
        if choice == "hetero":
            workload = "synthetic"
            main(
                 fsize=fsize,
                 path=res_root + "/hetero.csv",
                 Pol=[
                      "edf0", 
                      "edf1", 
                      "edf2", 
                      "edf3", 
                      # "edf4", 
                      "AVSched0",
                      "AVSched1",
                      "AVSched2",
                      "AVSched3",
                      # "AVSched4"
                     ],
                 Prob=[0.1, 0.2, 0.3],
                 basePol=[
                          ("edf0", False),
                          # ("edf4", False),
                          ("edf3", False),
                          ("edf2", False),
                          ("edf1", False)
                          ],
                 competingPol=[
                               ("AVSched0", True),
                               # ("AVSched4", True),
                               ("AVSched3", True),
                               ("AVSched2", True),
                               ("AVSched1", True)],
                 Drop=[True, False],
                 bbox=(0.5, 1.1),
                 ncol=5,
                 Ylabs=["AVSched", "", "", "", ""])
        if choice == "ad":
            width=.4
            workload = "ad"
            main(
                 fsize=fsize,
                 path=res_root + "/ad.csv",
                 Pol=[
                      "CATS", 
                      "CPATH", 
                      "2step_EDF", 
                      "RHEFT", 
                      "AVSched"
                     ],
                 Prob=[0.1, 0.2, 0.3],
                 basePol=[
                          ("CATS", False),
                          ("CPATH", False),
                          ("2step_EDF", False),
                          ("RHEFT", False)
                          ],
                 competingPol=[
                               ("AVSched", True),
                               ("AVSched", True),
                               ("AVSched", True),
                               ("AVSched", True),
                               ("AVSched", True)],
                 Drop=[True, False],
                 bbox=(0.5, 1.1),
                 ncol=5,
                 Ylabs=["CATS", "CPATH", "BSF-EDF", "RHEFT"]
                 )
        if choice == "mapping":
            width=.4
            workload = "mav"
            main(
                 fsize=fsize,
                 path=res_root + "/mapping.csv",
                 Pol=[
                      "CATS", 
                      "CPATH", 
                      "2STEP_EDF", 
                      "RHEFT", 
                      "AVSched"
                     ],
                 Prob=[0.1, 0.2, 0.3],
                 basePol=[
                          ("CATS", False),
                          ("CPATH", False),
                          ("2STEP_EDF", False),
                          ("RHEFT", False)
                          ],
                 competingPol=[
                               ("AVSched", True),
                               ("AVSched", True),
                               ("AVSched", True),
                               ("AVSched", True)],
                 Drop=[True, False],
                 bbox=(0.5, 1.1),
                 ncol=5,
                 Ylabs=["CATS", "CPATH", "BSF-EDF", "RHEFT"]
                 )
        if choice == "packing":
            width=.4
            workload = "mav"
            main(
                 fsize=fsize,
                 path=res_root + "/packing.csv",
                 Pol=[
                      "CATS", 
                      "CPATH", 
                      "2STEP_EDF", 
                      "RHEFT", 
                      "AVSched"
                     ],
                 Prob=[0.1, 0.2, 0.3],
                 basePol=[
                          ("CATS", False),
                          ("CPATH", False),
                          ("2STEP_EDF", False),
                          ("RHEFT", False)
                          ],
                 competingPol=[
                               ("AVSched", True),
                               ("AVSched", True),
                               ("AVSched", True),
                               ("AVSched", True)],
                 Drop=[True, False],
                 bbox=(0.5, 1.1),
                 ncol=5,
                 Ylabs=["CATS", "CPATH", "BSF-EDF", "RHEFT"]
                 )
        # main(
        #      fsize=(3.5,3.25),
        #      path=res_root + "/rank_update.csv",
        #      Pol=["MS1", "MS2", "MS1_Update", "MS2_Update"],
        #      Prob=[0.1, 0.2, 0.3],
        #      basePol=[("MS1", True),
        #               ("MS2", True)],
        #      Drop=[True],
        #      ncol=3)
        # main(
        #      fsize=(3.5,3.25),
        #      path=res_root + "/motiv.csv",
        #      Pol=["2step_EDF", "MS1_Update", "MS2_Update"],
        #      Prob=[0.1, 0.2, 0.3],
        #      basePol=("2step_EDF", False),
        #      Drop=[True, False],
        #      ncol=3)
