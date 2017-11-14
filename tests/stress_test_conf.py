"""Configure for Stress Testing ASCAR Services

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
import logging
import socket
from typing import List

__author__ = 'Yan Li'
__copyright__ = 'Copyright (c) 2016, 2017 The Regents of the University of California. All rights reserved.'

"""Maps hostname to MA ID
"""
nodeid_map = {
    'ryu.soe.ucsc.edu': 1,
    'zangief.soe.ucsc.edu': 3,
    'guile.soe.ucsc.edu': 4,
    'blanka.soe.ucsc.edu': 5,
}

TICK_LEN = 1

# create a long list of pseudo-random data
PAYLOAD_LEN = 1000
payload1 = [x * 4 for x in range(PAYLOAD_LEN)]
payload2 = [x * 8 for x in range(PAYLOAD_LEN)]


def ma_collector1() -> List[float]:
    return payload1


def ma_collector2() -> List[float]:
    return payload2


def lustre_controller(cpvs: List[float]):
    pass

# The following instr. must be in online using single quote. Don't break it or the
# runner shell script won't be able to read it.
stress_test_clients=['ryu.soe.ucsc.edu', 'blanka.soe.ucsc.edu', 'zangief.soe.ucsc.edu', 'guile.soe.ucsc.edu']

opt = {
    'tick_len': TICK_LEN,               # duration of a tick in second
    'nodeid_map': nodeid_map,
    'dbfile': '/tmp/test_db.sqlite',

    # Collectors are functions that collect PIs. MA calls them in order and concatenate
    # their returns into a single list before passing them to IntfDaemon
    'collectors': [ma_collector1, ma_collector2],
    'intf_daemon_loc': 'sagat.soe.ucsc.edu:9123',
    'ascar.MonitorAgent.MonitorAgent_logfile': '/tmp/test_ma_log.txt',
    'ascar.IntfDaemon.IntfDaemon_logfile': '/tmp/test_intfdaemon_log.txt',
    'loglevel': logging.DEBUG,
    'pidfile_dir': '/tmp',

    'controller': lustre_controller,
}
