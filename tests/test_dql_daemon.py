#!/usr/bin/env python

"""Test cases for ASCAR Deep Q Learning Daemon."""

import logging
import os
import threading
import time
import unittest
from . import common
from ascar.DQLDaemon import DQLDaemon
from ascar.tf_rl.simulation import discrete_hill
import ascar.ascar_logging

__author__ = 'Yan Li'
__copyright__ = 'Copyright (c) 2016, 2017 The Regents of the University of California. All rights reserved.'

ascar.ascar_logging.set_log_level(logging.WARN)


class TestDQLDaemon(unittest.TestCase):
    dqldaemon = None           # type: DQLDaemon
    game = None
    nodeid_map = None          # type: dict
    test_db_file = '/tmp/ascar-drl-testdb'

    def _dqldaemon_thread_func(self):
        opt = {'nodeid_map': self.nodeid_map,
               'dbfile': self.test_db_file,
               'delay_between_actions': 0,
               'exploration_period': 10,     # make it very short
               }
        self.game = discrete_hill.DiscreteHill()
        self.dqldaemon = DQLDaemon(opt, self.game)
        assert not self.dqldaemon.is_game_over()
        assert self.dqldaemon.is_stopped()
        self.dqldaemon.start()

    def setUp(self):
        # set up testdb
        self.nodeid_map = common.testdb_nodeid_map
        common.populate_testdb(self.test_db_file)
        save_path = os.path.dirname(self.test_db_file)
        try:
            os.remove(os.path.join(save_path, 'model'))
            os.remove(os.path.join(save_path, 'deepq_state'))
        except FileNotFoundError:
            pass

    def test_start_stop(self):
        threading.Thread(target=self._dqldaemon_thread_func).start()
        while not self.dqldaemon:
            time.sleep(0.1)
        self.dqldaemon.stop()
        self.dqldaemon.join()
        assert self.dqldaemon.is_stopped()
        self.game = None
        self.dqldaemon = None

    def test_discrete_hill(self):
        threading.Thread(target=self._dqldaemon_thread_func).start()
        total_waiting_time = 0
        while True:
            if self.dqldaemon and self.dqldaemon.is_game_over():
                break
            time.sleep(1)
            total_waiting_time += 1
            self.assertLess(total_waiting_time, 300, 'Timeout. Engine failed to converge.')

        # See if the target has been reached in discrete hill
        assert self.game.position == self.game.target
        self.game = None
        self.dqldaemon = None

    def test_discrete_hill_save_and_restore(self):
        threading.Thread(target=self._dqldaemon_thread_func).start()
        total_waiting_time = 0
        total_waiting_time2 = 0
        print("1st run current position: " + str(self.game.position))
        while True:
            if self.dqldaemon and self.dqldaemon.is_game_over():
                print("1st runtime: " + str(total_waiting_time))
                break
            time.sleep(1)
            total_waiting_time += 1
        print("1st run target position: " + str(self.game.target))
        run_steps = self.dqldaemon.test_number_of_steps_after_restore
        print(run_steps)
        self.dqldaemon.stop()
        self.dqldaemon.join()
        del self.game
        del self.dqldaemon
        threading.Thread(target=self._dqldaemon_thread_func).start()
        print("2nd run current position: " + str(self.game.position))
        print("2nd target position: "+ str(self.game.target))
        while True:
            if self.dqldaemon and self.dqldaemon.is_game_over():
                print("2nd runtime: " + str(total_waiting_time2))
                break
            time.sleep(1)
            total_waiting_time2 += 1
        run_steps2 = self.dqldaemon.test_number_of_steps_after_restore
        print(run_steps2)
        self.dqldaemon.stop()
        self.dqldaemon.join()

        self.assertEqual(run_steps, 0)
        self.assertLess(run_steps, run_steps2)
        self.assertLess(total_waiting_time2,total_waiting_time)
        # See if the target has been reached in discrete hill
        #assert self.game.position == self.game.target
        del self.game
        del self.dqldaemon

if __name__ == '__main__':
    unittest.main()
