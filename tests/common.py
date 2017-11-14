"""Common routines for test cases

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
import os
import time
from ascar import ReplayDB

__author__ = 'Yan Li'
__copyright__ = 'Copyright (c) 2016, 2017 The Regents of the University of California. All rights reserved.'

testdb_nodeid_map = {'blanka': 1, 'dhalsim': 2, 'gouken': 3, 'ryu': 4, 'seth': 5}
num_obd = 4
pi_per_obd = 6
xstart = 0
dbopt = {
    'nodeid_map': testdb_nodeid_map,
    'tick_data_size': num_obd * pi_per_obd * len(testdb_nodeid_map),
    'obd_per_client_ma': num_obd,
    'pi_per_client_obd': pi_per_obd,
    'num_actions': 1
}
num_ticks = 47
first_ts = None
last_ts = None


def populate_testdb(test_db_file: str) -> ReplayDB:
    global first_ts, last_ts
    dbopt['dbfile'] = test_db_file
    try:
        os.remove(test_db_file)
    except FileNotFoundError:
        pass
    db = ReplayDB(dbopt)

    homedir = os.path.dirname(os.path.abspath(__file__))
    dsdir = os.path.join(homedir, '../datasets/iorcp_2013-11-30_N5-b4g_a0.999_b100tau_472/'
                                  'iorcp_2013-11-28_07-11-54_MPIIO_w_N5_d0_i1_s1_F_b4g_t256m_s1_stat_log/')
    # map hostname to ma_id
    cur_ts = int(time.time())
    last_ts = cur_ts - 1
    first_ts = last_ts - num_ticks + 1
    for host in testdb_nodeid_map.keys():
        with open(os.path.join(dsdir, '{0}.stat_log'.format(host)), 'rt') as csvfile:
            csvreader = csv.reader(csvfile, delimiter=' ')
            for row in csvreader:
                # we pretend the data were collect num_ticks seconds ago
                ts = cur_ts - num_ticks + int(row[0])
                # make sure the input data is not corrupted
                assert len(row) == num_obd * pi_per_obd + 1
                pis = [int(x) for x in row[1:]]
                db.insert_pi(testdb_nodeid_map[host], ts, pis)
    # inserting dummy action
    for xs in range(cur_ts - (num_ticks+1) + xstart, cur_ts):
        db.insert_action(xs, 1)

    return db


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("""Usage: {0} testdb
Generate and pre-populate testdb""".format(sys.argv[0]))
        exit(2)
    populate_testdb(sys.argv[1])
