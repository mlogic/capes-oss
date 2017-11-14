#!/bin/bash
# Stress test the Interface Daemon
# 
# Copyright (c) 2016, 2017 The Regents of the University of California. All
# rights reserved.
# 
# Created by Yan Li <yanli@tuneup.ai>, Kenneth Chang <kchang44@ucsc.edu>,
# Oceane Bel <obel@ucsc.edu>. Storage Systems Research Center, Baskin School
# of Engineering.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#     * Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice, this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the Storage Systems Research Center, the
#       University of California, nor the names of its contributors
#       may be used to endorse or promote products derived from this
#       software without specific prior written permission.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# REGENTS OF THE UNIVERSITY OF CALIFORNIA BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.
set -e -u
cd `dirname $0`
. config
TEST_NAME=`basename ${0}`
LOG_DIR=${LOG_DIR}/${TEST_NAME}/`date +%Y-%m-%d_%H-%M-%S`

echo "Reading configuration from stress_test_conf.py"
INTF_DAEMON_LOC=`grep intf_daemon_loc stress_test_conf.py | cut -d"'" -f4`
INTF_DAEMON_HOST=`echo $INTF_DAEMON_LOC | cut -d":" -f1`
CLIENTS=`grep stress_test_clients stress_test_conf.py | cut -d"[" -f2 | cut -d"]" -f1 | sed -e "s/'//g" | sed -e "s/,//g"`

cleanup()
{
    set +e
    ssh $INTF_DAEMON_HOST /share/drl/intfdaemon_service.sh /share/drl/tests/stress_test_conf.py stop
    for CLIENT in $CLIENTS; do
        ssh $CLIENT /share/drl/ma_service.sh /share/drl/tests/stress_test_conf.py stop
    done
    exit 255
}

echo "Cleaning up old test logs"
for CLIENT in $CLIENTS; do
    ssh ${CLIENT} rm -f /tmp/test_ma_log.txt\*
done
rm -f /tmp/test_db.sqlite
rm -f /tmp/test_intfdaemon_log.txt*

trap cleanup EXIT
echo "Starting services"
ssh $INTF_DAEMON_HOST /share/drl/intfdaemon_service.sh /share/drl/tests/stress_test_conf.py start
sleep 2
for CLIENT in $CLIENTS; do
    ssh $CLIENT /share/drl/ma_service.sh /share/drl/tests/stress_test_conf.py start
done

echo "Waiting for ${STRESS_TEST_DURATION} seconds"
sleep ${STRESS_TEST_DURATION}

trap "" EXIT
set +e
echo "Stopping services"
for CLIENT in $CLIENTS; do
    ssh $CLIENT /share/drl/ma_service.sh /share/drl/tests/stress_test_conf.py stop
done
sleep 2
ssh $INTF_DAEMON_HOST /share/drl/intfdaemon_service.sh /share/drl/tests/stress_test_conf.py stop

set -e

# Archive the results
mkdir -p ${LOG_DIR}/intf_daemon
mv /tmp/test_db.sqlite ${LOG_DIR}/intf_daemon/
mv /tmp/test_intfdaemon_log.txt* ${LOG_DIR}/intf_daemon/
for CLIENT in $CLIENTS; do
    mkdir -p ${LOG_DIR}/${CLIENT}
    scp ${CLIENT}:/tmp/test_ma_log.txt\* ${LOG_DIR}/${CLIENT}
done

# Check results
pushd ${LOG_DIR} >/dev/null
SAVED_MSGS=`sqlite3 intf_daemon/test_db.sqlite "select count(ma_id) from pis;"`
EXP_MSGS=`grep "Collected" *.soe.ucsc.edu/test_ma_log.txt | wc -l`
popd >/dev/null

if [ $SAVED_MSGS -eq $EXP_MSGS ]; then
    echo "$TEST_NAME PASS"
else
    echo "$TEST_NAME FAILED. Expected messages: $EXP_MSGS, actual messages: $SAVED_MSGS"
    exit 1
fi
