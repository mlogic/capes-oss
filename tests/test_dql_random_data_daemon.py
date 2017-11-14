#!/usr/bin/env python

#Tests for the ReplayDB that will help us connect and test the DB -> DRL connection

import time
import unittest
import logging
from ascar import IntfDaemon
from ascar import MonitorAgent
from ascar import ControlAgent
from ascar import ReplayDB
from ascar import PythonQLearning
from ascar import LustreCommon
from random import randint



class TestRandomDataEntryDQL(unittest.TestCase):
    port = 9123
    test_db_file = '/tmp/ascar-drl-testdb'

    def test_data_retrieval(self):
        #connecting the drl module to the database
        PythonQLearning.connect_db(self.test_db_file)
        ARRAY_TS = []
        #preparing test data to send to the database
        for x in range(7):
            ts = int(time.time())
            ARRAY_TS.append(ts)
            testdata = [ts, 1*x, 2*x, 3*x, 4*x, 5*x, 6*x, 7*x]
            #sending the test data to the test database
            db = ReplayDB(self.test_db_file)
            data = [LustreCommon.protocol_ver, x] + testdata
            db.insert_pi(x,ts,data[1:])

        #randomInt = randint(0,6)
        ARRAY_TEST = PythonQLearning.getRandomDataFromDB()
        print(ARRAY_TEST[2:])
        ma_id = ARRAY_TEST[0]
        tstest = ARRAY_TEST[1]

        print("ma_id = " +str(ma_id)+ " tstest = "+str(tstest))

        #Now time to get the data from the database into the drl
        self.assertEqual(ReplayDB(self.test_db_file).get_pi(ma_id, tstest)[2:], ARRAY_TEST[2:], 'The ma_id gotten is {0} and the tstest value is {1}'.format(ma_id,tstest))




if __name__ == '__main__':
    unittest.main()