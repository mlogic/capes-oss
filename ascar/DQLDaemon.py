#!/usr/bin/env python

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

import gc
import os
import tempfile
import tensorflow as tf
import time
import traceback
from .ascar_logging import *
from .tf_rl.controller import DiscreteDeepQ
from .tf_rl.models import MLP


__author__ = 'Yan Li'
__copyright__ = 'Copyright (c) 2016, 2017 The Regents of the University of California. All rights reserved.'


class DQLDaemon:
    """DQLDaemon of ASCAR

    All public members are thread-safe.

    :type controller: DiscreteDeepQ
    :type opt: dict
    :type session: tf.Session

    """
    controller = None
    debugging_level = 0
    delay_between_actions = 1           # seconds between actions
    disable_training = False
    exploration_period = 5000
    opt = None
    last_observation = None
    last_action = None
    new_action = None
    save_path = None
    session = None
    start_random_rate = 0.5
    test_number_of_steps_after_restore = 0

    def __init__(self, opt: dict = None, game=None):
        if 'dqldaemon_debugging_level' in opt:
            self.debugging_level = opt['dqldaemon_debugging_level']
        self.stop_requested = False
        self.stopped = True
        self.opt = opt
        self.save_path = os.path.dirname(opt['dbfile'])
        if game:
            self.game = game
        else:
            from .LustreGame import Lustre
            self.opt['disable_same_thread_check'] = True
            self.game = Lustre(self.opt, lazy_db_init=True)
        if 'delay_between_actions' in opt:
            self.delay_between_actions = opt['delay_between_actions']
        if 'exploration_period' in opt:
            self.exploration_period = opt['exploration_period']
        if 'start_random_rate' in opt:
            self.start_random_rate = opt['start_random_rate']
        self.enable_tuning = self.opt.get('enable_tuning', True)
        self.LOG_DIR = tempfile.mkdtemp()

    def start(self):
        if self.debugging_level >= 1:
            import cProfile
            import io
            import pstats
            pr = cProfile.Profile()
            pr.enable()

        self.stopped = False
        try:
            self.game.connect_db()

            # TensorFlow business - it is always good to reset a graph before creating a new controller.
            tf.reset_default_graph()
            # TODO: shall we use InteractiveSession()?
            self.session = tf.Session()  # tf.InteractiveSession()

            # This little guy will let us run tensorboard
            #      tensorboard --logdir [LOG_DIR]
            journalist = tf.train.SummaryWriter(self.LOG_DIR)

            # Brain maps from observation to Q values for different actions.
            # Here it is a done using a multi layer perceptron with 2 hidden
            # layers
            hidden_layer_size = max(int(self.game.observation_size * 1.2), 200)
            logger.info('Observation size {0}, hidden layer size {1}'.format(self.game.observation_size,
                                                                             hidden_layer_size))
            brain = MLP([self.game.observation_size, ], [hidden_layer_size, hidden_layer_size, self.game.num_actions],
                        [tf.tanh, tf.tanh, tf.identity])

            # The optimizer to use. Here we use RMSProp as recommended
            # by the publication
            optimizer = tf.train.RMSPropOptimizer(learning_rate=0.001, decay=0.9)

            # DiscreteDeepQ object
            self.controller = DiscreteDeepQ((self.game.observation_size,), self.game.num_actions, brain, optimizer,
                                            self.session, discount_rate=0.99, start_random_rate=self.start_random_rate,
                                            exploration_period=self.exploration_period,
                                            random_action_probability=self.opt.get('random_action_probability', 0.05),
                                            train_every_nth=1, summary_writer=journalist)

            self.session.run(tf.initialize_all_variables())

            self.session.run(self.controller.target_network_update)

            #checks if there is a model to be loaded before updating the graph
            if os.path.isfile(os.path.join(self.save_path, 'model')):
                self.controller.restore(self.save_path)
                logger.info('Loaded saved model from ' + self.save_path)
            else:
                logger.info('No saved model found')

            self.test_number_of_steps_after_restore = self.controller.actions_executed_so_far



            # graph was not available when journalist was created
            journalist.add_graph(self.session.graph)

            logger.info('DQLDaemon started')

            last_action_second = 0
            last_training_step_duration = 0
            last_checkpoint_time = time.time()
            while not self.stop_requested:
                begin_time = time.time()
                minibatch_size, prediction_error = self._do_training_step()
                if minibatch_size > 0:
                    if time.time() - last_checkpoint_time > 60*30:
                        # Checkpoint every 30 minutes. TODO: make this a parameter.
                        cp_path = os.path.join(self.save_path, 'checkpoint_' + time.strftime('%Y-%m-%d_%H-%M-%S'))
                        os.mkdir(cp_path)
                        self.controller.save(cp_path)
                        last_checkpoint_time = time.time()
                        logger.info('Checkpoint saved in ' + cp_path)
                    last_training_step_duration = time.time() - begin_time
                    logger.info('Finished {step}th training step in {time} seconds '
                                'using {mb} samples with prediction error {error}.'.format(
                                    step=self.controller.iteration, time=last_training_step_duration, mb=minibatch_size,
                                    error=prediction_error))
                else:
                    logger.info('Not enough data for training yet.')

                if self.game.is_over():
                    logger.info('Game over')
                    self.stop_requested = True
                    return

                ts = time.time()
                if ts - (last_action_second+0.5) >= self.delay_between_actions - last_training_step_duration:
                    if self.enable_tuning:
                        try:
                            self.game.refresh_memcache()
                        except:
                            pass

                        sleep_time = max(0, self.delay_between_actions - (time.time() - (last_action_second + 0.5)))
                        if sleep_time > 0.05:
                            # Do cleaning up before long sleeping
                            gc.collect()
                            sleep_time = max(0, self.delay_between_actions - (time.time() - (last_action_second + 0.5)))
                        if sleep_time > 0.0001:
                            logger.debug('Sleeping {0} seconds'.format(sleep_time))
                            time.sleep(sleep_time)
                        self._do_action_step()
                        last_action_second = int(time.time())
                    else:
                        logger.debug('Tuning disabled.')
                        # Check for new data every 200 steps to reduce checking overhead
                        if self.controller.number_of_times_train_called % 200 == 0:
                            try:
                                self.game.refresh_memcache()
                            except:
                                pass
                    # We always print out the reward to the log for analysis
                    logger.info('Cumulative reward: {0}'.format(self.game.cumulative_reward))

                    flush_log()
        finally:
            self.stopped = True
            self.controller.save(self.save_path)
            logger.info('DQLDaemon stopped. Model saved in ' + self.save_path)

            if self.debugging_level >= 1:
                pr.disable()
                s = io.StringIO()
                sortby = 'cumulative'
                ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
                ps.print_stats()
                print(s.getvalue())

    def _do_training_step(self) -> (int, float):
        """ Do a training step

        This function is NOT thread-safe and can only be called within the worker thread.

        :return: size of the mini batch, prediction error
        """
        if not self.disable_training:
            mini_batch = self.game.get_minibatch()
            if mini_batch:
                logger.debug('Got minibatch of size {0}'.format(len(mini_batch)))
                return len(mini_batch), self.controller.training_step(mini_batch)
            else:
                return 0, None
        else:
            raise RuntimeError('Training is disabled')

    def _do_action_step(self):
        """ Do an action step

        This function is NOT thread-safe and can only be called within the worker thread.

        :return:
        """
        if not self.enable_tuning:
            raise RuntimeError('Tuning is disabled')

        try:
            new_observation = self.game.observe()
            reward = self.game.collect_reward()
        except BaseException as e:
            logger.info('{0}. Skipped taking action.'.format(str(e)))
            traceback.print_exc()
            return

        # Store last transition. This is only needed for the discrete hill test case.
        if self.last_observation is not None:
            self.game.store(self.last_observation, self.last_action, reward, new_observation)

        # act
        self.new_action = self.controller.action(new_observation)
        self.game.perform_action(self.new_action)

        self.last_action = self.new_action
        self.last_observation = new_observation

    def is_game_over(self) -> bool:
        """Check if the game is over

        This function is thread-safe

        :return: A bool that represents if the game is over
        """
        # First check if the game is stopped, if not we can't safely read self.game
        if not self.is_stopped():
            return False

        return self.game.is_over()

    def is_stopped(self) -> bool:
        """ Check if the worker thread is stopped

        This function is thread-safe.

        :return:
        """
        return self.stopped

    def join(self):
        while not self.stopped:
            time.sleep(0.2)

    def stop(self):
        """ Stop the daemon

        This function is thread-safe.
        :return:
        """
        self.stop_requested = True
        logger.info('Requesting DQLDaemon to stop...')
