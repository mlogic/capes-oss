"""Configure for Testing ASCAR DQL Services

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
from tests import common
import logging

__author__ = 'Yan Li'
__copyright__ = 'Copyright (c) 2016, 2017 The Regents of the University of California. All rights reserved.'

TICK_LEN = 1

cpvs = [
        # name, min, max, step size
        ['rtt_ratio_changepoint', 237, 37, 437, 10],
        ['ewma_changepoint_a', 41001, 20001, 60001, 1000],
        ['ewma_changepoint_b', 48427, 28427, 68427, 1000],
    ]

opt = {
    'tick_len': TICK_LEN,               # duration of a tick in second
    'nodeid_map': common.testdb_nodeid_map,
    'tick_data_size': common.dbopt['tick_data_size'],
    'dbfile': '/tmp/test_db.sqlite',
    'obd_per_client_ma': common.dbopt['obd_per_client_ma'],
    'pi_per_client_obd': common.dbopt['pi_per_client_obd'],

    # Collectors are functions that collect PIs. MA calls them in order and concatenate
    # their returns into a single list before passing them to IntfDaemon
    'intf_daemon_loc': 'localhost:9123',
    'ascar.IntfDaemon.IntfDaemon_logfile': '/tmp/test_intfdaemon_log.txt',
    'ascar.DQLDaemon.DQLDaemon_logfile': '/tmp/test_dqldaemon_log.txt',
    'loglevel': logging.DEBUG,
    'pidfile_dir': '/tmp',

    'start_random_rate': 1,
    'exploration_period': 10000,
    'cpvs': cpvs,
    'num_actions': 2*len(cpvs)+1,
}
