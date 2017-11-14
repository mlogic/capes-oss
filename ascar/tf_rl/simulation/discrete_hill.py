"""
based on https://github.com/nivwusquorum/tensorflow-deepq under
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

from collections import deque
from random import randint, gauss
import random
import time
import numpy as np


class DiscreteHill(object):
    num_actions = 5
    observation_size = 5
    actionNumber = 0
    directions = [(0,0),(0,1), (0,-1), (1,0), (-1,0)]
    reward = 0

    def __init__(self, board=(10,10), variance=4., store_every_nth=5, minibatch_size=32, max_experience=30000):
        self.variance = variance
        self.target = (0,0)
        while self.target == (0,0):
            self.target   = (randint(-board[0], board[0]), randint(-board[1], board[1]))
        self.position = (0,0)

        self.shortest_path = self.distance(self.position, self.target)

        self.number_of_times_store_called = 0
        self.store_every_nth = store_every_nth
        self.experience = deque()
        self.minibatch_size = minibatch_size
        self.max_experience = max_experience

    def connect_db(self):
        pass

    @staticmethod
    def add(p, q):
        return p[0] + q[0], p[1] + q[1]

    @staticmethod
    def distance(p, q):
        return abs(p[0] - q[0]) + abs(p[1] - q[1])

    def estimate_distance(self, p):
        distance = DiscreteHill.distance(self.target, p) - DiscreteHill.distance(self.target, self.position)
        return distance + abs(gauss(0, self.variance))

    def observe(self):
        return np.array([self.estimate_distance(DiscreteHill.add(self.position, delta))
                         for delta in DiscreteHill.directions])

    def perform_action(self, action):
        self.actionNumber = action
        self.reward = - DiscreteHill.distance(self.target, DiscreteHill.add(self.position, DiscreteHill.directions[action])) \
                      + DiscreteHill.distance(self.target, self.position) - 2
        self.position = DiscreteHill.add(self.position, DiscreteHill.directions[action])

    def is_over(self):
        return self.position == self.target

    @property
    def cumulative_reward(self):
        return 0

    def collect_reward(self):
        reward = self.reward
        self.reward = 0
        return reward
        #print(DiscreteHill.distance(self.target, self.position))
        #currentreward = 100-DiscreteHill.distance(self.target,self.position)
        #if currentreward < 0:
        #    currentreward = 0
        #currentreward = currentreward/100
        #print("current reward for the action: "+ str(currentreward))
        #return currentreward

    def store(self, observation, action, reward, newobservation):
        """Store experience, where starting with observation and
        execution action, we arrived at the newobservation and got thetarget_network_update
        reward reward

        If newstate is None, the state/action pair is assumed to be terminal
        """
        if self.number_of_times_store_called % self.store_every_nth == 0:
            self.experience.append((observation, action, reward, newobservation, time.time()))
            if len(self.experience) > self.max_experience:
                self.experience.popleft()
        self.number_of_times_store_called += 1

    def get_minibatch(self):
        if len(self.experience) < self.minibatch_size:
            return None

        # sample experience.
        samples = random.sample(range(len(self.experience)), self.minibatch_size)
        samples = [self.experience[i] for i in samples]
        return samples
