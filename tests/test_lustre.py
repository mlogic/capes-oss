#!/usr/bin/env python

"""Test cases for the ReplayDB

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

from copy import deepcopy
import logging
import numpy as np
import os
import random
import unittest
from ascar import ascar_logging
from ascar import ReplayDB, NotEnoughDataError
from ascar import LustreCommon
from . import common
from ascar import LustreGame

__author__ = 'Oceane Bel, Yan Li'
__copyright__ = 'Copyright (c) 2016, 2017 The Regents of the University of California. All rights reserved.'

ascar_logging.set_log_level(logging.WARN)


class TestLustre(unittest.TestCase):
    """ Test cases for LustreGame

    :type db: ReplayDB
    :type nodeid_map: dict
    """
    db = None
    nodeid_map = None
    test_db_file = '/tmp/ascar-drl-testdb'
    opt = None

    def setUp(self):
        self.db = common.populate_testdb(self.test_db_file)
        self.nodeid_map = common.testdb_nodeid_map
        self.opt = deepcopy(common.dbopt)

    def tearDown(self):
        self.db.conn.close()

    def test_memcache(self):
        l = LustreGame.Lustre(self.opt)
        for i in range(l.ticks_per_observation - 1):
            with self.assertRaises(NotEnoughDataError):
                l.get_observation_by_cache_idx(i)

        with self.assertRaises(NotEnoughDataError):
            l.get_next_observation_by_cache_idx(common.num_ticks - 1)

        l.get_next_observation_by_cache_idx(common.num_ticks - 2)

    def test_get_minibatch_32(self):
        l = LustreGame.Lustre(self.opt)
        mb = l.get_minibatch_from_db()
        self.assertEqual(l.minibatch_size, len(mb))
        random_index = random.randint(0, len(mb) - 1)

        random_ts = mb[random_index][4]
        exp_observation = self.db.get_observation(random_ts)
        # See if we can find identical data of this random_ts. Syntax explanation: https://stackoverflow.com/a/9542768
        act_observation = next(x for x in mb if x[4] == random_ts)[0]

        self.assertTrue(np.array_equal(act_observation, exp_observation))
        self.assertEqual(l.minibatch_size, len(mb))

    def test_get_minibatch_32_from_memcache(self):
        l = LustreGame.Lustre(self.opt)
        mb = l.get_minibatch()
        self.assertEqual(l.minibatch_size, len(mb))
        for observ, action, reward, observ_next, ts in mb:
            self.assertTrue(np.array_equal(observ, l.db.get_observation(ts)))
            self.assertTrue(np.array_equal(observ_next, l.db.get_observation(ts+1)))
            self.assertEqual(action, l.db.get_action(ts))
            # TODO(yanli): check reward

    def test_get_minibatch_100(self):
        self.opt['minibatch_size'] = 100
        l = LustreGame.Lustre(self.opt)
        minibatch = l.get_minibatch()
        self.assertEqual(common.num_ticks - l.ticks_per_observation, len(minibatch))
        random_index = random.randint(0, len(minibatch) - 1)

        random_ts = minibatch[random_index][4]
        exp_observation = self.db.get_observation(random_ts)
        # See if we can find identical data of this random_ts. Syntax explanation: https://stackoverflow.com/a/9542768
        act_observation = next(x for x in minibatch if x[4] == random_ts)[0]
        self.assertTrue(np.array_equal(act_observation, exp_observation))

        # simulate the case when one action is missing
        c = self.db.conn.cursor()
        c.execute('DELETE FROM actions WHERE ts = 25')
        self.db.conn.commit()
        self.assertEqual(0, self.db.get_action(25))
        minibatch = l.get_minibatch()
        # the minibatch should still have the same amount of samples with one sample has action == 0
        self.assertEqual(common.num_ticks - l.ticks_per_observation, len(minibatch))

        c.execute('DELETE FROM actions')
        self.db.conn.commit()
        self.assertIsNone(l.get_minibatch_from_db())

    def test_not_enough_action(self):
        """This test case only applies to get_minibatch_from_db(). get_minibatch() (the memcache version) always
        treats missing actions as 0."""
        common.xstart = 23
        db2 = common.populate_testdb(self.test_db_file)
        self.assertEqual(db2.get_action_row_count(), common.num_ticks - 23 + 1)
        l = LustreGame.Lustre(self.opt)
        minibatch = l.get_minibatch_from_db()
        self.assertEqual(common.num_ticks - common.xstart, len(minibatch))

        random_index = random.randint(0, len(minibatch) - 1)
        random_ts = minibatch[random_index][4]
        exp_observation = db2.get_observation(random_ts)
        # See if we can find identical data of this random_ts. Syntax explanation: https://stackoverflow.com/a/9542768
        act_observation = next(x for x in minibatch if x[4] == random_ts)[0]

        self.assertTrue(np.array_equal(act_observation, exp_observation))

    def test_collect_pi_cpv(self):
        import_data = """import:
name: lustrefs-OST0003-osc-ffff880414c43400
target: lustrefs-OST0003_UUID
state: FULL
instance: 1
connect_flags: [write_grant, server_lock, version, request_portal, truncate_lock, max_byte_per_rpc, early_lock_cancel, adaptive_timeouts, lru_resize, alt_checksum_algorithm, fid_is_enabled, version_recovery, full20, layout_lock, 64bithash, object_max_bytes, jobstats, einprogress, lvb_type]
import_flags: [replayable, pingable]
connection:
   failover_nids: [128.114.52.68@tcp]
   current_connection: 128.114.52.68@tcp
   connection_attempts: 1
   generation: 1
   in-progress_invalidations: 0
rpcs:
   inflight: 0
   unregistering: 0
   timeouts: 0
   avg_waittime: 296 usec
   ack_ewma: 111.222 usec
   sent_ewma: 333.444 usec
   rtt_ratio100: 555.666
service_estimates:
   services: 1 sec
   network: 1 sec
transactions:
   last_replay: 0
   peer_committed: 0
   last_checked: 0
read_throughput: 777.888
write_throughput: 888.999
"""

        self.assertAlmostEqual(111.222, LustreCommon.extract_ack_ewma_from_import(import_data))
        self.assertAlmostEqual(333.444, LustreCommon.extract_sent_ewma_from_import(import_data))
        self.assertAlmostEqual(555.666, LustreCommon.extract_rtt_ratio100_from_import(import_data))
        self.assertAlmostEqual(777.888, LustreCommon.extract_read_bandwidth_from_import(import_data))
        self.assertAlmostEqual(888.999, LustreCommon.extract_write_bandwidth_from_import(import_data))

    def test_reward_functions(self):
        nodeid_map = {
            'ryu.soe.ucsc.edu': 1,
            'sagat.soe.ucsc.edu': 2,
            'zangief.soe.ucsc.edu': 3,
            'guile.soe.ucsc.edu': 4,
            'blanka.soe.ucsc.edu': 5,
            'ken.soe.ucsc.edu': 6,
            'vega.soe.ucsc.edu': 7,
            'abel.soe.ucsc.edu': 8
        }
        opt = {
            'dbfile': os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                   '../datasets/filebench_2016-09-05_18-14-07/ascar_replay_db.sqlite'),
            'nodeid_map': nodeid_map,
            'clients': [
                'ryu.soe.ucsc.edu',
                'sagat.soe.ucsc.edu',
                'zangief.soe.ucsc.edu',
                'guile.soe.ucsc.edu'],
            'pi_per_client_obd': 8,
            'obd_per_client_ma': 4,
            'tick_data_size': 8 * 4 * 4,   # see conf.py for explanation
            'num_actions': 1,              # unused
            'missing_entry_tolerance': 0,
        }
        l = LustreGame.Lustre(opt)
        self.assertAlmostEqual(1.21978880e+07 + 5.42585720e+07 + 1.57655040e+07 + 6.11041280e+07,
                               l.cumulative_reward)

        self.assertEqual(l._calc_total_throughput(l.db.get_observation(1473124606)) -
                         l._calc_total_throughput(l.db.get_observation(1473124605)),
                         l.collect_reward())

    def test_gen_rule(self):
        template = """8,2
0,{{ cpv2 }},{{ cpv2 }},48551,0,{{ cpv1 }},-1,-176,32840
0,{{ cpv3 }},0,41104,0,{{ cpv1 }},-1,-176,32840
{{ cpv3 }},2147483647,{{ cpv3 }},2147483647,{{ cpv1 }},2147483647,-1,-58,33980"""
        exp_rule = """8,2
0,444,444,48551,0,333,-1,-176,32840
0,555.1,0,41104,0,333,-1,-176,32840
555.1,2147483647,555.1,2147483647,333,2147483647,-1,-58,33980"""
        self.assertEqual(exp_rule, LustreCommon.gen_rule(template, {'cpv1': 333, 'cpv2': 444, 'cpv3': 555.1}))


if __name__ == '__main__':
    unittest.main()
