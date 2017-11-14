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

import numpy as np
import unittest
from ascar import NotEnoughDataError
from ascar import ReplayDB
from ascar import LustreGame
from . import common

__author__ = 'Oceane Bel, Yan Li'
__copyright__ = 'Copyright (c) 2016, 2017 The Regents of the University of California. All rights reserved.'


class TestReplayDB(unittest.TestCase):
    """ Test cases for ReplayDB

    :type db: ReplayDB
    :type nodeid_map: dict
    """
    db = None
    nodeid_map = None
    test_db_file = '/tmp/ascar-drl-testdb'

    def setUp(self):
        self.db = common.populate_testdb(self.test_db_file)
        self.nodeid_map = common.testdb_nodeid_map
        self.opt = common.dbopt

    def test_get_observation(self):
        ts = self.db.get_last_ts()
        self.assertEqual(common.last_ts, ts)
        obs = self.db.get_observation(ts - common.num_ticks + 26)
        # observation should be sorted by MA ID
        # blanka: 1
        exp_obs = np.array([
            68140, 70908, 402, 1, 40396, 22020096, 56112, 57510, 293, 1, 40396, 19922944, 57133, 55209, 341, 1, 40396,
            22020096, 57047, 61719, 361, 2, 40396, 24117248,
            45642, 47516, 254, 1, 32840, 22020096, 36120, 39135, 242, 1, 32840, 22020096, 51568, 52817, 206, 1, 40396,
            23068672, 46591, 46726, 285, 4, 32840, 19922944,
            37058, 34825, 287, 1, 32840, 17825792, 70221, 72842, 249, 1, 40396, 28311552, 45684, 45039, 169, 1, 32840,
            20971520, 51986, 50942, 302, 3, 40396, 23068672,
            52184, 49322, 231, 1, 40396, 26214400, 39298, 41973, 168, 1, 32840, 17825792, 51535, 49789, 295, 1, 40396,
            26214400, 47524, 51471, 166, 2, 33980, 23068672
        ], dtype=float)
        # dhalsim: 2
        exp_obs = np.append(exp_obs, [
            44672, 45032, 344, 1, 32840, 28311552, 47702, 47393, 359, 3, 32840, 25165824, 40484, 42136, 269, 1, 32840,
            18874368, 29907, 32180, 575, 1, 33980, 22020096,
            71347, 68676, 228, 1, 40396, 16777216, 43211, 42763, 304, 1, 32840, 25165824, 42580, 42751, 316, 1, 32840,
            27262976, 45113, 45804, 410, 1, 32840, 24117248,
            55170, 52614, 828, 1, 33980, 23068672, 42609, 41687, 335, 1, 32840, 22020096, 42459, 42359, 259, 1, 32840,
            22020096, 33002, 38247, 1532, 1, 33980, 26214400,
            34712, 32994, 262, 1, 32840, 17825792, 43073, 44087, 135, 1, 32840, 24117248, 44707, 46093, 575, 1, 33980,
            25165824, 74802, 76575, 279, 1, 40396, 25165824,
        ])
        # gouken: 3
        exp_obs = np.append(exp_obs, [
            38596, 37619, 350, 1, 32840, 18874368, 51683, 51510, 333, 1, 40396, 30408704, 61910, 58733, 283, 1, 40396,
            20971520, 60315, 56297, 287, 2, 40396, 20971520,
            44296, 44129, 255, 1, 32840, 26214400, 58944, 55465, 1213, 1, 40396, 19922944, 39664, 40037, 347, 1, 32840,
            20971520, 39313, 40251, 240, 1, 32840, 22020096,
            52859, 51982, 219, 1, 40396, 24117248, 45125, 45227, 224, 1, 32840, 14680064, 48504, 45885, 399, 1, 33980,
            22020096, 53535, 50686, 270, 1, 33980, 20971520,
            78392, 86948, 334, 1, 40396, 13631488, 39997, 38007, 270, 1, 32840, 28311552, 41975, 42880, 307, 1, 32840,
            24117248, 41229, 40395, 296, 1, 32840, 25165824
        ])
        # ryu: 4
        exp_obs = np.append(exp_obs, [
            44618, 44803, 286, 4, 32840, 24117248, 58567, 58088, 231, 1, 40396, 24117248, 46106, 50170, 255, 1, 33980,
            22020096, 45173, 46716, 262, 1, 32840, 24117248,
            50793, 50951, 251, 3, 40396, 24117248, 44843, 42653, 377, 1, 32840, 20971520, 46149, 48234, 336, 1, 32840,
            24117248, 41938, 40991, 185, 1, 32840, 24117248,
            44656, 44092, 164, 1, 32840, 23068672, 43573, 45397, 166, 1, 32840, 24117248, 42911, 45031, 240, 1, 32840,
            19922944, 60013, 61752, 243, 1, 40396, 22020096,
            61485, 60927, 362, 1, 40396, 23068672, 45752, 47223, 146, 1, 32840, 24117248, 39219, 38875, 276, 1, 32840,
            27262976, 42183, 44488, 191, 1, 32840, 20971520,
        ])
        # seth: 5
        exp_obs = np.append(exp_obs, [
            51745, 51235, 211, 5, 40396, 25165824, 46701, 47343, 316, 1, 32840, 29360128, 51581, 55075, 277, 1, 40396,
            24117248, 49948, 50423, 195, 1, 40396, 19922944,
            51418, 54090, 275, 7, 40396, 22020096, 48995, 47562, 275, 1, 33980, 25165824, 33803, 35038, 289, 1, 32840,
            29360128, 64600, 65689, 319, 1, 40396, 18874368,
            68445, 70700, 206, 9, 40396, 18874368, 54304, 51380, 337, 1, 40396, 18874368, 79158, 75985, 154, 1, 40396,
            14680064, 60275, 60124, 586, 1, 33980, 22020096,
            48790, 48884, 294, 10, 40396, 22020096, 48906, 49216, 1150, 1, 33980, 22020096, 63492, 56481, 240, 1, 40396,
            18874368, 53556, 52403, 560, 1, 40396, 22020096
        ])
        self.assertTrue(np.array_equal(exp_obs, obs))

        # Test fetching from memcache
        l = LustreGame.Lustre(self.opt)
        self.assertTrue(np.array_equal(exp_obs, l.get_observation_by_cache_idx(25)))
        last_ts_data = self.db.get_last_n_observation()[0]
        self.assertTrue(np.array_equal(last_ts_data, l.observe()))
        del l

        # Introducing a missing entry
        c = self.db.conn.cursor()
        c.execute('DELETE FROM pis WHERE ts = ? AND ma_id=3', (ts - common.num_ticks + 25,))
        self.db.conn.commit()
        ticks_per_observation = 4
        # calculate the location of the hole
        hole_start = 2 * common.num_obd * common.pi_per_obd * ticks_per_observation +\
                     2 * common.num_obd * common.pi_per_obd
        hole_end = hole_start + common.num_obd * common.pi_per_obd
        exp_obs[hole_start:hole_end] = 0
        obs = self.db.get_observation(ts - common.num_ticks + 26)
        self.assertTrue(np.array_equal(exp_obs, obs))
        # Test fetching with hole from memcache
        l = LustreGame.Lustre(self.opt)
        self.assertTrue(np.array_equal(exp_obs, l.get_observation_by_cache_idx(25)))
        del l

        # We remove one MA's data from the last ts and see if get_last_ts() returns ts-1
        c.execute('DELETE FROM pis WHERE ts = ? AND ma_id=3', (common.last_ts,))
        self.db.conn.commit()
        self.assertEqual(common.last_ts-1, self.db.get_last_ts())
        # Observe should return the ts-1 data because ts has a hole larger than missing entry tolerance
        self.opt['missing_entry_tolerance'] = 0
        l = LustreGame.Lustre(self.opt)
        second_last_ts_data = l.db.get_last_n_observation()[0]
        self.assertFalse(np.array_equal(last_ts_data, second_last_ts_data))
        self.assertTrue(np.array_equal(second_last_ts_data, l.observe()))
        del l
        # It should still return last ts data if we raise the missing entry tolerance
        self.opt['missing_entry_tolerance'] = 1
        l = LustreGame.Lustre(self.opt)
        hole_start = 2 * common.num_obd * common.pi_per_obd * ticks_per_observation +\
                     3 * common.num_obd * common.pi_per_obd
        hole_end = hole_start + common.num_obd * common.pi_per_obd
        last_ts_data[hole_start:hole_end] = 0
        self.assertTrue(np.array_equal(last_ts_data, l.observe()))
        self.assertTrue(np.array_equal(last_ts_data, l.db.get_last_n_observation()[0]))
        del l

        # Introduce a big hole
        c.execute('INSERT INTO pis SELECT ma_id, ts+100 AS ts, pi_data FROM pis')
        self.db.conn.commit()
        l = LustreGame.Lustre(self.opt)
        for i in range(common.num_ticks, common.num_ticks+3):
            with self.assertRaises(NotEnoughDataError):
                l.get_observation_by_cache_idx(i)
        self.assertTrue(np.array_equal(exp_obs, l.get_observation_by_cache_idx(25 + common.num_ticks)))
        del l

if __name__ == '__main__':
    unittest.main()
