"""ASCAR Deep Q Learning Daemon.

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

Some of the code are based on https://github.com/nivwusquorum/tensorflow-deepq under
the following license:

The MIT License (MIT)

Copyright (c) 2015 Szymon Sidor

Permission is hereby granted, free of charge, to any person obtaining a copy of this
software and associated documentation files (the "Software"), to deal in the Software
without restriction, including without limitation the rights to use, copy, modify,
merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
permit persons to whom the Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be included in all copies
or substantial portions of the Software.
"""

from copy import deepcopy
import numpy as np
import random
import resource
import time
from .ReplayDB import *
from .IntfDaemon import IntfDaemon
from .ascar_logging import logger

__author__ = 'Yan Li'
__copyright__ = 'Copyright (c) 2016, 2017 The Regents of the University of California. All rights reserved.'


MemcacheEntryPIs = Tuple[int, np.ndarray]
MemcacheEntry = Tuple[int, int, List[MemcacheEntryPIs]]  # (ts, action, PIs)


class Lustre(object):
    """ The Lustre Game Class

    :type cpvs: List[float]
    :type db: ReplayDB
    :type memcache: List[MemcacheEntry]
    :type opt: dict
    :type pi_per_client_obd: int
    """
    cpvs = None
    db = None
    memcache = None
    memcache_bad_idx = set()
    memcache_last_rowid = 0
    num_actions = None
    ticks_per_observation = 4

    # for unit test
    TestSample = []

    def __init__(self, opt, lazy_db_init=False):
        """Construct a Lustre game

        :param opt:
        :param minibatch_size: size of the minibatch
        :param lazy_db_init: If true, the DB connection won't be created until connect_db() is called.
                             Useful if the DB connection should be opened in another thread.
        """

        self.opt = deepcopy(opt)
        self.ticks_per_observation = opt.get('ticks_per_observation', 4)
        self.pi_per_client_obd = opt['pi_per_client_obd']
        self.observation_size = opt['tick_data_size'] * self.ticks_per_observation
        self.minibatch_size = opt.get('minibatch_size', 32)
        if not lazy_db_init:
            self.connect_db()
        self.num_actions = opt['num_actions']

    def connect_db(self):
        if not self.db:
            self.db = ReplayDB(self.opt)

        self.refresh_memcache()

    @staticmethod
    def is_over():
        return False

    @staticmethod
    def store(*unused):
        pass

    def perform_action(self, action_id: int):
        """Send the new action to IntfDaemon
        """
        assert 0 <= action_id < self.num_actions

        if not self.cpvs:
            # use the default value
            self.cpvs = [x[1] for x in self.opt['cpvs']]

        if action_id > 0:
            cpv_id = (action_id - 1) // 2
            lower_range = self.opt['cpvs'][cpv_id][2]
            upper_range = self.opt['cpvs'][cpv_id][3]
            step = self.opt['cpvs'][cpv_id][4]
            if action_id % 2 == 0:
                # minus step
                if self.cpvs[cpv_id] < lower_range + step:
                    # invalid move, do nothing
                    pass
                else:
                    self.cpvs[cpv_id] -= step
            else:
                # plus 1
                if self.cpvs[cpv_id] > upper_range - step:
                    # invalid move, do nothing
                    pass
                else:
                    self.cpvs[cpv_id] += step

        # Broadcast action must begin with action_id, which will be saved by
        # IntfDaemon to the DB.
        IntfDaemon.broadcast_action([action_id] + self.cpvs)

    def observe(self) -> np.ndarray:
        """Return observation vector using memcache.
        """
        err_msg = 'No valid observation in the past two seconds'
        if len(self.memcache) < self.ticks_per_observation:
            raise NotEnoughDataError(err_msg)
        for idx in range(len(self.memcache)-1, max(len(self.memcache)-3, self.ticks_per_observation-1), -1):
            try:
                return self.get_observation_by_cache_idx(idx)
            except NotEnoughDataError:
                pass
        raise NotEnoughDataError(err_msg)

    def observe_from_db(self) -> np.ndarray:
        """Return observation vector using ReplayDB.
        """
        return self.db.get_last_n_observation()[0]

    @property
    def cumulative_reward(self):
        try:
            return self._calc_total_throughput(self.db.get_last_n_observation()[0])
        except NotEnoughDataError:
            return 0

    def collect_reward(self):
        """Reward is the sum of read throughput + write throughput of clients
        """
        o, prevo = self.db.get_last_n_observation(2)
        return self._calc_total_throughput(o) - self._calc_total_throughput(prevo)

    def _calc_total_throughput(self, o: np.ndarray) -> float:
        """Calculate total throughput of an observation

        Only the throughput of last tick in the observation are included in the reward.
        :param o: observation
        :return: total throughput
        """
        if 'clients' in self.opt:
            num_ma = len(self.opt['clients'])
        elif 'num_ma' in self.opt:
            num_ma = self.opt['num_ma']
        else:
            num_ma = len(self.opt['nodeid_map'])
        # reshape also checks the shape of o
        o = np.reshape(o, (num_ma, self.ticks_per_observation,
                           self.opt['obd_per_client_ma'] * self.pi_per_client_obd))
        result = 0.0
        for ma_id in range(num_ma):
            for osc in range(self.opt['obd_per_client_ma']):
                read_tp_ix  = osc * (self.pi_per_client_obd-1) + 5
                write_tp_ix = osc * (self.pi_per_client_obd-1) + 6

                read_tp  = o[ma_id, self.ticks_per_observation-1, read_tp_ix]
                write_tp = o[ma_id, self.ticks_per_observation-1, write_tp_ix]
                # sanity check: our machine can't be faster than 300 MB/s
                assert 0 <= read_tp <= 300 * 1024 * 1024
                assert 0 <= write_tp <= 300 * 1024 * 1024
                result += read_tp + write_tp
        return result

    def refresh_memcache(self):
        logger.info('Loading cache')
        c = self.db.conn.cursor()
        # Use a large arraysize to increase read speed; we don't care about memory usage
        c.arraysize = 1000000
        if not self.memcache:
            self.memcache = list()
        preloading_cache_size = len(self.memcache)
        c.execute('''SELECT pis.rowid, pis.ma_id, pis.ts, pi_data, action
                     FROM pis LEFT JOIN actions ON pis.ts=actions.ts
                     WHERE pis.rowid > ? ORDER BY pis.ts, pis.ma_id''',
                  (self.memcache_last_rowid,))
        f = c.fetchall()
        for row in f:
            self.memcache_last_rowid = max(self.memcache_last_rowid, row[0])
            ma_id, ts, pi_data = row[1], row[2], pickle.loads(row[3])
            action = row[4] if row[4] else 0
            if ma_id not in self.db.ordered_client_list:
                continue
            assert len(pi_data) == self.db.tick_data_size // len(self.db.ordered_client_list)

            if len(self.memcache) == 0 or self.memcache[-1][0] != ts:
                self.memcache.append((ts, action, [None] * len(self.db.ordered_client_list)))
            self.memcache[-1][2][self.db.ordered_client_list.index(ma_id)] = np.array(pi_data)

        # Peak memory usage (bytes on OS X, kilobytes on Linux)
        # https://stackoverflow.com/a/7669482
        logger.info('Finished loading {len} entries. Peak memory usage {size:,}.'.format(
            len=len(self.memcache) - preloading_cache_size,
            size=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss))

    def get_minibatch_from_db(self):
        good_ts = set()
        bad_ts = set()
        result = []
        required_samples = self.minibatch_size
        while True:
            try:
                # DB data may change during our run so we query it every time
                min_ts, max_ts = self.db.get_action_ts_range()
                pi_min_ts, pi_max_ts = self.db.get_pi_ts_range()
            except NotEnoughDataError:
                return None
            # we need at least ticks_per_observation+1 ticks for one sample
            if (pi_max_ts - pi_min_ts < self.ticks_per_observation) or \
               (max_ts - min_ts < self.ticks_per_observation):
                return None
            # Calculate the starting ts after which we can take valid observation samples
            min_ts = max(min_ts, pi_min_ts + self.ticks_per_observation - 1)
            # total possible sample size after removing the first (ticks_per_observation-1) ticks
            # and the last tick (because we need ts+1 in the sample)
            total_sample_size = max_ts - min_ts - len(bad_ts)
            if total_sample_size <= len(result):
                return result
            required_samples = min(total_sample_size, required_samples)
            samples = random.sample(range(min_ts, max_ts), required_samples - len(result))
            for ts in samples:
                if ts in good_ts or ts in bad_ts:
                    continue
                try:
                    observ = self.db.get_observation(ts)
                    observ_next = self.db.get_observation(ts + 1)
                    reward = self._calc_total_throughput(observ_next) - self._calc_total_throughput(observ)
                    # The final ts is only used in test cases
                    result.append((observ, self.db.get_action(ts), reward, observ_next, ts))

                    good_ts.add(ts)
                    if len(result) == required_samples:
                        self.TestSample = list(good_ts)
                        return result
                except NotEnoughDataError:
                    logger.warning('NotEnoughDataError for ts {0}'.format(ts))
                    bad_ts.add(ts)

    def get_observation_by_cache_idx(self, idx: int) -> np.ndarray:
        assert 0 <= idx < len(self.memcache)
        if idx < self.ticks_per_observation - 1:
            raise NotEnoughDataError
        # Return None if the time is not continuous
        idx_start = idx - self.ticks_per_observation + 1
        if self.memcache[idx_start][0] != self.memcache[idx][0] - self.ticks_per_observation + 1:
            raise NotEnoughDataError('Not enough tick data')
        result = np.zeros((len(self.db.ordered_client_list),
                           self.ticks_per_observation,
                           int(self.db.tick_data_size / len(self.db.ordered_client_list))), dtype=float)
        missing_entry = 0
        for i in range(idx_start, idx+1):
            for ma_id_idx in range(len(self.db.ordered_client_list)):
                if self.memcache[i][2][ma_id_idx] is None:
                    missing_entry += 1
                    if missing_entry > self.db.missing_entry_tolerance:
                        raise NotEnoughDataError('Too many missing entries')
                else:
                    result[ma_id_idx, i-idx_start] = self.memcache[i][2][ma_id_idx]
        return result.reshape((self.observation_size,))

    def get_next_observation_by_cache_idx(self, idx: int) -> np.ndarray:
        assert 0 <= idx < len(self.memcache)
        if idx == len(self.memcache) - 1:
            raise NotEnoughDataError
        if self.memcache[idx][0] + 1 != self.memcache[idx + 1][0]:
            raise NotEnoughDataError
        return self.get_observation_by_cache_idx(idx + 1)

    def get_minibatch(self):
        # We need at least ticks_per_observation+1 ticks for one sample
        if len(self.memcache) < self.ticks_per_observation + 1:
            return None
        good_idx = set()
        result = []
        required_samples = self.minibatch_size
        while True:
            # total possible sample size after removing the first (ticks_per_observation-1) ticks
            # and the last tick (because we need ts+1 in the sample)
            total_sample_size = len(self.memcache) - self.ticks_per_observation - len(self.memcache_bad_idx)
            if total_sample_size <= len(result):
                return result
            required_samples = min(total_sample_size, required_samples)
            # The last idx has to be excluded so it won't be added to bad_idx set
            samples = random.sample(range(self.ticks_per_observation - 1, len(self.memcache)-1),
                                    required_samples - len(result))
            for i in samples:
                if i in good_idx or i in self.memcache_bad_idx:
                    continue
                try:
                    observ = self.get_observation_by_cache_idx(i)
                    observ_next = self.get_next_observation_by_cache_idx(i)
                    reward = self._calc_total_throughput(observ_next) - self._calc_total_throughput(observ)
                    # The final ts is only used in test cases
                    ts = self.memcache[i][0]
                    result.append((observ, self.memcache[i][1], reward, observ_next, ts))

                    good_idx.add(ts)
                    if len(result) == required_samples:
                        return result
                except NotEnoughDataError:
                    logger.info('NotEnoughDataError for memcache idx {0}'.format(i))
                    self.memcache_bad_idx.add(i)
