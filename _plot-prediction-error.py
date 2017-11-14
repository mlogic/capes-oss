#!/usr/bin/env python

"""Plot predictoin error

Copyright (c) 2016, 2017 The Regents of the University of California. All
rights reserved.

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

import csv
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
matplotlib.rc('font', family='serif', serif=['Times New Roman'], size=14)

number_of_point_plot = 200

# debug level: 0, 1, or 2
debug = 0

if len(sys.argv) < 3:
    print("Usage:", sys.argv[0], "input_csv output_pdf")
    exit(2)

data = []
with open(sys.argv[1], 'r') as csvfile:
    csvreader = csv.reader(csvfile, delimiter='\n')
    for row in csvreader:
        data.append(float(row[0]))

train_step = np.zeros(number_of_point_plot)
merged_data = np.zeros(number_of_point_plot)
merge_every_points = len(data) // number_of_point_plot
for i in range(1, number_of_point_plot):
    raw_data_loc = i * merge_every_points
    merged_data[i] = np.average(data[(i - 1) * merge_every_points:raw_data_loc]) / 1e16
    train_step[i] = raw_data_loc

plt.plot(train_step, merged_data, linestyle='-', color='g', label='Prediction Error')

plt.title('Prediction error over time')
plt.xlabel('Training step')
plt.ticklabel_format(style='sci', axis='x', scilimits=(0, 0))
plt.ylabel('Prediction error')

fig = plt.gcf()
default_size = fig.get_size_inches()
fig.set_size_inches(default_size[0]/1.4, default_size[1]/1.4)

plt.tight_layout()
plt.savefig(sys.argv[2], format='pdf', bbox_inches='tight')
