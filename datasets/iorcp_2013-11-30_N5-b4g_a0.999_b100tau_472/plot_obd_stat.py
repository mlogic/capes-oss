#!/usr/bin/env python

# Plot output of ewma logger

# Copyright (c) 2013, University of California, Santa Cruz, CA, USA.
# Developers:
#   Yan Li <yanli@cs.ucsc.edu>
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Storage Systems Research Center, the
#       University of California, nor the names of its contributors
#       may be used to endorse or promote products derived from this
#       software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# REGENTS OF THE UNIVERSITY OF CALIFORNIA BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function
import sys
import csv
import numpy as np
import matplotlib
matplotlib.use('PDF')
# For double y-axis, see http://stackoverflow.com/questions/9103166/multiple-axis-in-matplotlib-with-different-scales
from mpl_toolkits.axes_grid1 import host_subplot
import mpl_toolkits.axisartist as AA
import matplotlib.pyplot as plt
## for Palatino and other serif fonts use:
#matplotlib.rc('font',**{'family':'sans-serif','sans-serif':['Palatino']})
#matplotlib.rc('font',**{'family':'sans-serif','sans-serif':['Helvetica']})
matplotlib.rc('font',**{'family':'serif','serif':['times'],'size':14})
matplotlib.rc('text', usetex=True)

# Plot no more than this max OBD to avoid cluttering the graph.
# Note: Write BW is always aggregated no matter how many OBDs are chosen here.
MAX_OBD=1
COLUMNS_PER_OBD=6
# debug level: 0, 1, or 2
debug = 0

if len(sys.argv) < 3:
    print("Usage:", sys.argv[0], "input_csv output_pdf")
    exit(2)

columns = []
seconds = []
# bandwidths
bws = []
with open(sys.argv[1], 'rb') as csvfile:
    csvreader = csv.reader(csvfile, delimiter=' ')
    for row in csvreader:
        seconds.append(int(row[0]))
        while len(columns) < len(row) - 1:
            columns.append([])
        for i in range(1, len(row)):
            columns[i-1].append(float(row[i]))

if len(columns) % COLUMNS_PER_OBD != 0:
    print("Error! Columns' number is not a multiplication of", COLUMNS_PER_OBD)
    exit(1)
obd_no = len(columns) / COLUMNS_PER_OBD
if debug >= 1:
    print("obd_no:", obd_no)
# Summarize bandwidth
for s in range(0, len(seconds)):
    bw = 0
    for i in range(obd_no):
        if debug >= 2:
            print("Bandwidth of line %d column %d: %d" % (s, i * COLUMNS_PER_OBD + 5, columns[i * COLUMNS_PER_OBD + 5][s]))
        bw += columns[i * COLUMNS_PER_OBD + 5][s]
    bws.append(bw/1000000)

columns_np = np.array(columns)
# How to set this for host?
# ymin, ymax = host.ylim()
# ymax = ymax * 1.15
# ymin = np.amin(columns_np)
# host.ylim(ymin, ymax)

# Add yscale='log' if you need logarithm scale y-axis
host = host_subplot(111, axes_class=AA.Axes)
plt.subplots_adjust(top=1-0.05)
plt.subplots_adjust(bottom=0.07)
plt.subplots_adjust(right=1-0.01)
plt.subplots_adjust(left=0.01)
par1 = host.twinx()
par2 = host.twinx()
par3 = host.twinx()
par_tau = host.twinx()

# offset = 37
# new_fixed_axis = par2.get_grid_helper().new_fixed_axis
# par2.axis["right"] = new_fixed_axis(loc="right",
#                                     axes=par2,
#                                     offset=(offset, 0))
# par2.axis["right"].toggle(all=True)
# new_fixed_axis = par3.get_grid_helper().new_fixed_axis
# par3.axis["right"] = new_fixed_axis(loc="right",
#                                     axes=par3,
#                                     offset=(offset * 2, 0))
# par3.axis["right"].toggle(all=True)
# new_fixed_axis = par_tau.get_grid_helper().new_fixed_axis
# par_tau.axis["right"] = new_fixed_axis(loc="right",
#                                     axes=par_tau,
#                                     offset=(offset * 3, 0))
# par_tau.axis["right"].toggle(all=True)

line_no = 0
# MAX_OBD is set to 1, and we only plot the first OBD
col_no = min(len(columns), MAX_OBD * COLUMNS_PER_OBD)
for i in range(0, col_no):
    if i % COLUMNS_PER_OBD == 0:
        columns[i] = map(lambda x: x/1000, columns[i])
        host.plot(seconds, columns[i], linestyle='-', marker='^', color='k', markersize=4, label='Ack EWMA')
    # Skip plotting send ewma because it's very similar to ack ewma
    # elif i % COLUMNS_PER_OBD == 1:
        # columns[i] = map(lambda x: x/1000, columns[i])
        # host.plot(seconds, columns[i], linestyle='-', color=color, markersize=4, label='Send EWMA')
    elif i % COLUMNS_PER_OBD == 2:
        columns[i] = map(lambda x: x/100, columns[i])
        par3.plot(seconds, columns[i], linestyle='-', marker='o', color='r', markersize=4, label='PT Ratio')
    elif i % COLUMNS_PER_OBD == 3:
        par1.plot(seconds, columns[i], linestyle='-', marker='*', color='b', markersize=4, label='Congestion window')
    elif i % COLUMNS_PER_OBD == 4:
        columns[i] = map(lambda x: x/1000, columns[i])
        par_tau.plot(seconds, columns[i], linestyle='-', color='g', markersize=4, label='$\\tau$')
    line_no += 1
par2.plot(seconds, bws, linestyle='--', linewidth=2, color='m', markersize=4, label='Bandwidth')

# Distribute the lines vertically so they won't overlap each other
plt.title('Client status')
host.set_xlabel('Time (second)')
# host.set_ylabel('EWMA of Intervals ($10^{-3}$ second)')
ymin,ymax = host.get_ylim()
ylen = ymax - ymin
host.set_ylim(ymin, ymax + ylen/2)

# par1.set_ylabel('Congestion window (max RPCs in flight')
ymin,ymax = par1.get_ylim()
ylen = ymax - ymin
par1.set_ylim(ymin - ylen, ymax + ylen*3.5)

# par2.set_ylabel('Bandwidth (MB/s)')
ymin,ymax = par2.get_ylim()
ylen = ymax - ymin
par2.set_ylim(ymin, ymax + ylen/6)

# par3.set_ylabel('PT Ratio')
ymin,ymax = par3.get_ylim()
par3.set_ylim(ymin, ymax*5)

# par_tau.set_ylabel('$\\tau$ ($10^{-3}$ second)')
ymin,ymax = par_tau.get_ylim()
ylen = ymax - ymin
par_tau.set_ylim(ymin, ymax - ylen/11)

host.legend(loc=0,prop={'size':14})
host.set_yticks([])
par1.set_yticks([])
par2.set_yticks([])
par3.set_yticks([])
par_tau.set_yticks([])
plt.savefig(sys.argv[2], format='pdf')
