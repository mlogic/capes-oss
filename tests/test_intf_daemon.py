#!/usr/bin/env python

"""Test cases for ASCAR Interface Daemon

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

import numpy as np
import logging
import os
import threading
import time
from typing import List
import unittest
from ascar import ascar_logging
from ascar.IntfDaemon import IntfDaemon
from ascar.MonitorAgent import MonitorAgent
from ascar import ReplayDB
from ascar.LustreGame import Lustre

__author__ = 'Yan Li'
__copyright__ = 'Copyright (c) 2016, 2017 The Regents of the University of California. All rights reserved.'

ascar_logging.set_log_level(logging.WARNING)

_total_actions = 0
_expected_controller_action_data = None


def _controller_action(data: List[float]):
    global _total_actions
    _total_actions += 1
    if _expected_controller_action_data:
        assert isinstance(data, list)
        assert _expected_controller_action_data == data


class TestIntfDaemon(unittest.TestCase):
    port = 9123
    test_db_file = '/tmp/ascar-drl-testdb'
    intf_daemon = None              # type: IntfDaemon
    ma_daemon = None                # type: MonitorAgent

    def _start_intf_daemon_func(self):
        assert self.intf_daemon
        self.intf_daemon.start()

    def _start_ma_daemon_func(self):
        assert self.ma_daemon
        self.ma_daemon.start()

    def test_start_stop(self):
        try:
            ma_id = 1
            opt = {
                'ma_id': ma_id,
                'intf_daemon_loc': 'localhost:{port}'.format(port=self.port),
                'dbfile': self.test_db_file,
                'controller': _controller_action,
                'tick_data_size': 3,
                'num_ma': 1,
            }
            self.intf_daemon = IntfDaemon(opt)
            self.intf_daemon_thread = threading.Thread(target=self._start_intf_daemon_func)
            self.intf_daemon_thread.start()

            self.ma_daemon = MonitorAgent(opt)
            ts = int(time.time())

            test_data = [ts, 1, 2, 3]
            self.ma_daemon.send_obj(test_data)
            time.sleep(0.5)

            # check the data is stored in db
            db = ReplayDB(opt)
            self.assertListEqual(test_data[1:], db.get_pi(ma_id, ts))

            # test broadcasting an action
            self.ma_daemon_thread = threading.Thread(target=self._start_ma_daemon_func)
            self.ma_daemon_thread.start()
            time.sleep(1)
            IntfDaemon.broadcast_action([42])
            time.sleep(1)
            ts = int(time.time())
            IntfDaemon.broadcast_action([42])
            time.sleep(1)
            IntfDaemon.broadcast_action([42])
            time.sleep(1)
            self.assertEqual(_total_actions, 3)
            self.assertEqual(42, db.get_action(ts))
        finally:
            # stop() function is thread-safe
            self.intf_daemon.stop()
            self.ma_daemon.stop()
            self.intf_daemon_thread.join()
            self.ma_daemon_thread.join()

    def test_calculating_cpvs(self):
        global _expected_controller_action_data
        try:
            ma_id = 1
            nodeid_map = {
                'foo': 1,
            }
            cpvs = [['mrif', 8, 1, 10, 1], ['other_cpv', 12345, 11000, 22345, 1000]]
            opt = {
                'ma_id': ma_id,
                'intf_daemon_loc': 'localhost:{port}'.format(port=self.port),
                'dbfile': self.test_db_file,
                'controller': _controller_action,
                'tick_data_size': 3,
                'nodeid_map': nodeid_map,
                'cpvs': cpvs,
                'num_actions': 2 * len(cpvs) + 1,
                'pi_per_client_obd': 1
            }
            try:
                os.remove(opt['dbfile'])
            except FileNotFoundError:
                pass
            # Don't store action to shorten testing
            self.intf_daemon = IntfDaemon(opt, store_action=False)
            self.intf_daemon_thread = threading.Thread(target=self._start_intf_daemon_func)
            self.intf_daemon_thread.start()

            self.ma_daemon = MonitorAgent(opt)
            self.ma_daemon_thread = threading.Thread(target=self._start_ma_daemon_func)
            self.ma_daemon_thread.start()
            time.sleep(0.5)

            # check the action is correctly handled
            l = Lustre(opt)
            # default CPV values
            _expected_controller_action_data = [0, 8, 12345]
            l.perform_action(0)
            time.sleep(0.1)

            _expected_controller_action_data = [0, 8, 12345]
            l.perform_action(0)
            time.sleep(0.1)

            _expected_controller_action_data = [0, 9, 12345]
            l.perform_action(1)
            time.sleep(0.1)

            _expected_controller_action_data = [0, 10, 12345]
            l.perform_action(1)
            time.sleep(0.1)

            # First CPV shouldn't go over 10
            _expected_controller_action_data = [0, 10, 12345]
            l.perform_action(1)
            time.sleep(0.1)

            _expected_controller_action_data = [0, 9, 12345]
            l.perform_action(2)
            time.sleep(0.1)

            _expected_controller_action_data = [0, 9, 11345]
            l.perform_action(4)
            time.sleep(0.1)

            # CPV2 can't go lower than 11000 and should stay at 11345
            _expected_controller_action_data = [0, 9, 11345]
            l.perform_action(4)
            time.sleep(0.1)

            _expected_controller_action_data = [0, 9, 12345]
            l.perform_action(3)
            time.sleep(0.1)
        finally:
            # stop() function is thread-safe
            self.intf_daemon.stop()
            self.ma_daemon.stop()
            self.intf_daemon_thread.join()
            self.ma_daemon_thread.join()
            _expected_controller_action_data = None

if __name__ == '__main__':
    unittest.main()
