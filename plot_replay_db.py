#!/usr/bin/env python
"""Plot using data from a replay DB

Copyright (c) 2013, 2014, 2015, 2016 The Regents of the University
of California. All rights reserved.

Created by Yan Li <yanli@tuneup.ai>, Kenneth Chang <kchang44@ucsc.edu>,
Oceane Bel <obel@ucsc.edu>. Storage Systems Research Center, Baskin School
of Engineering.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the Storage Systems Research Center, the
      University of California, nor the names of its contributors
      may be used to endorse or promote products derived from this
      software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
REGENTS OF THE UNIVERSITY OF CALIFORNIA BE LIABLE FOR ANY DIRECT,
INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import getopt
import sys
import numpy as np
import matplotlib
import sqlite3
import pickle

# This line has to be here before we do the following
matplotlib.use('PDF')
# For double y-axis, see http://stackoverflow.com/questions/9103166/multiple-axis-in-matplotlib-with-different-scales
from mpl_toolkits.axes_grid1 import host_subplot
import mpl_toolkits.axisartist as AA
import matplotlib.pyplot as plt

obd_per_client_ma = 4
pi_per_client_obd = 11
number_of_point_plot = 70


def find_gap(db_name: str):
    c = sqlite3.connect(db_name).cursor()
    c.execute('SELECT ts from pis ORDER BY ts DESC')

    last_ts = None
    if debug >= 2:
        print('Finding gap...')
    while True:
        row = c.fetchone()
        if not row:
            # no gap found
            if debug >= 2:
                print('No gap in database')
            return 0
        if not last_ts:
            last_ts = row[0]
        else:
            if last_ts - row[0] > 10:
                if debug >= 2:
                    print('Found gap at {gap}'.format(gap=last_ts))
                # found the last gap
                return last_ts
            else:
                last_ts = row[0]


def read_db_data(db_name, start_ts=0):
    conn = sqlite3.connect(db_name)
    data = conn.cursor().execute('SELECT ma_id, ts, pi_data FROM pis WHERE ts >= ? ORDER BY ts, ma_id',
                                 (start_ts,)).fetchall()

    if debug >= 2:
        print('Total row: {0}'.format(len(data)))
    imported_data = dict()
    prev_ts = data[0][1]
    mrif = None
    total_tp = 0
    tau = None
    for row in data:
        ma_id = row[0]
        ts = row[1]
        pis = pickle.loads(row[2])
        try:
            if ts != prev_ts:
                if mrif is not None and tau is not None:
                    imported_data[prev_ts] = [total_tp, mrif, tau]
                total_tp = 0
            if len(pis) == 0:
                # Skip MA's that doesn't send in data
                continue
            # mrif = Maximum RPCs (Remote procedure calls) in flight.
            # AKA the max number of remote code calls currently being executed
            mrif = pis[0]
            for osc in range(obd_per_client_ma):
                read_tp_ix = osc * (pi_per_client_obd - 1) + 5
                write_tp_ix = osc * (pi_per_client_obd - 1) + 6
                tau_ix = osc * (pi_per_client_obd - 1) + 7

                read_tp = pis[read_tp_ix]
                write_tp = pis[write_tp_ix]
                tau = pis[tau_ix]
                # sanity check: our machine can't be faster than 300 MB/s
                assert 0 <= read_tp <= 300 * 1024 * 1024
                assert 0 <= write_tp <= 300 * 1024 * 1024
                total_tp += read_tp + write_tp

        finally:
            prev_ts = ts

    # need to add that last ts explicitly
    imported_data[ts] = [total_tp, mrif, tau]

    if print_mode:
        print('ts,total_tp,mrif,tau')
        for ts, data in sorted(imported_data.items()):
            print('{ts},{total_tp},{mrif},{tau}'.format(ts=ts, total_tp=data[0], mrif=data[1], tau=data[2]))
        exit(0)

    seconds = []
    total_tp_array = np.zeros(number_of_point_plot)
    tau_array = []
    reward_array = []

    sorted_data = sorted(imported_data.items())
    # we don't sample mrif
    mrif = [x[1][1] for x in sorted_data]
    all_tp = np.array([x[1][0] for x in sorted_data])
    merge_every_points = max(1, len(sorted_data) // number_of_point_plot)

    for i in range(number_of_point_plot):
        raw_data_loc = i * merge_every_points
        seconds.append(sorted_data[raw_data_loc][0])
        total_tp_array[i] = np.average(all_tp[(i-1)*merge_every_points:raw_data_loc]) / 1000000
        tau_array.append(sorted_data[raw_data_loc][1][2] / 1000)

    reward_array.append(0)
    for i in range(len(total_tp_array)):
        reward = 0
        next_index = i + 1
        if i < len(total_tp_array) - 1:
            reward = total_tp_array[next_index] - total_tp_array[i]
            reward_array.append(reward)

    # taking of the smallest timestamp on every other timestamp
    ts_at_zero = seconds[0]
    for i in range(len(seconds)):
        seconds[i] = seconds[i] - ts_at_zero

    if debug >= 2:
        print('len(reward_array): {0}'.format(len(reward_array)))
        print('len(seconds): {0}'.format(len(seconds)))
    return seconds, mrif, total_tp_array, tau_array, reward_array


## for Palatino and other serif fonts use:
#matplotlib.rc('font',**{'family':'sans-serif','sans-serif':['Palatino']})
#matplotlib.rc('font',**{'family':'sans-serif','sans-serif':['Helvetica']})
matplotlib.rc('font', family='serif', serif=['times'], size=16)
#matplotlib.rc("font", family="serif", size=12)
matplotlib.rc('text', usetex=True)

if len(sys.argv) < 3:
    print("""Usage: {bin} [-p] [-g] [-b baseline_db] input_db output_pdf
-b      Plot the data from baseline_db as the baseline.
-p      Just print out the throughput in CSV.
-g      Only plot the data after the last gap. The default is to plot everything.
-t      Plot MRIF, tau, and reward.
-v      Verbose mode.
""".format(bin=sys.argv[0]))
    exit(2)

optlist, args = getopt.getopt(sys.argv[1:], 'b:pgtv')
optlist = dict(optlist)
debug = 2 if '-v' in optlist else 0
baseline_db = optlist.get('-b', None)
print_mode = '-p' in optlist
find_gap_mode = '-g' in optlist
if debug >= 2 and find_gap_mode:
    print('find gap mode enabled')
plot_cpv = '-t' in optlist
db_name = args[0]
start_ts = find_gap(db_name) if find_gap_mode else 0

seconds, mrif, total_tp_array, tau_array, reward_array = read_db_data(db_name, start_ts)
if baseline_db:
    baseline_start_ts = find_gap(baseline_db)
    _, _, baseline_tp, _, _ = read_db_data(baseline_db, baseline_start_ts)
    if len(baseline_tp) > len(total_tp_array):
        baseline_tp = baseline_tp[:len(total_tp_array)]

output_pdf = args[1]
host = host_subplot(111, axes_class=AA.Axes)
plt.subplots_adjust(top=1-0.05)
plt.subplots_adjust(bottom=0.07)
plt.subplots_adjust(right=1-0.01)
plt.subplots_adjust(left=0.01)
par1 = host.twinx()
if plot_cpv:
    par2 = host.twinx()
    par3 = host.twinx()
    offset = 37
    new_fixed_axis = par2.get_grid_helper().new_fixed_axis
    par2.axis["right"] = new_fixed_axis(loc="right",
                                        axes=par2,
                                        offset=(offset*2, 0))
    par2.axis["right"].toggle(all=True)

    new_fixed_axis = par3.get_grid_helper().new_fixed_axis
    par3.axis["right"] = new_fixed_axis(loc="right",
                                        axes=par3,
                                        offset=(offset*4, 0))
    par3.axis["right"].toggle(all=True)

host.plot(seconds, total_tp_array, linestyle='-', color='r', markersize=4, label='CAPES tuned throughput')
if baseline_db:
    host.plot(seconds[:len(baseline_tp)], baseline_tp, linestyle='dashed', color='b', markersize=4, label='baseline throughput')
par1.plot(range(len(mrif)), mrif, linestyle='-', color='k', markersize=4, label='congestion window size')
if plot_cpv:
    par2.plot(seconds, tau_array, linestyle='-', marker='.', color='r', markersize=4, label='tau')
    par3.plot(seconds, reward_array, linestyle='-', marker='o', color='g', markersize=4, label='reward')

plt.title('Throughput During the Tuning Process')
host.set_xlabel('Time (seconds)')
host.set_ylabel('Throughput (MB/s)')
ymin, ymax = host.get_ylim()
host.set_ylim(ymin, ymax)

par1.set_ylabel('Congestion window size')
ymin, ymax = par1.get_ylim()
par1.set_ylim(ymin, ymax)
if plot_cpv:
    par2.set_ylabel('tau')
    par3.set_ylabel('reward')

    ymin, ymax = par2.get_ylim()
    par2.set_ylim(ymin, ymax)

    ymin, ymax = par3.get_ylim()
    par3.set_ylim(ymin, ymax)

host.legend(loc=0, prop={'size': 16})
plt.savefig(output_pdf, format='pdf', bbox_inches='tight')
