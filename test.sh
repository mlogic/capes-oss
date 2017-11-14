#!/bin/bash
set -e -u
cd `dirname $0`

python -m unittest tests.test_common.TestCommon
python -m unittest tests.test_intf_daemon.TestIntfDaemon
python -m unittest tests.test_ReplayDB.TestReplayDB
python -m unittest tests.test_dql_daemon.TestDQLDaemon
python -m unittest tests.test_lustre.TestLustre
tests/test_ma_service.sh
tests/test_intfdaemon_service.sh
tests/test_dqldaemon_service.sh
