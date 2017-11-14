#!/bin/bash
# Testing the DQL Daemon Service
#
# We start an IntfDaemon and an DQLDaemon with a prepopulated database,
# and check if DQLDaemon is sending out actions every second.
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
cd `dirname $0`/..
. _check.sh
export PYTHONPATH=.

DQLDAEMON_SERVICE_CMD="./dqldaemon_service.sh tests/test_dqldaemon_conf.py"
INTFDAEMON_SERVICE_CMD="./intfdaemon_service.sh tests/test_dqldaemon_conf.py"
$DQLDAEMON_SERVICE_CMD status | grep -q "not running"
$INTFDAEMON_SERVICE_CMD status | grep -q "not running"

# create the test db
rm -f /tmp/test_db.sqlite
python tests/common.py /tmp/test_db.sqlite

rm -f /tmp/model
rm -f /tmp/deepq_state
rm -f /tmp/test_intfdaemon_log.txt*
rm -f /tmp/test_dqldaemon_log.txt*

cleanup() {
    set +e
    $DQLDAEMON_SERVICE_CMD stop
    $INTFDAEMON_SERVICE_CMD stop
    exit 255
}

trap "cleanup" EXIT
$INTFDAEMON_SERVICE_CMD start
sleep 1
$DQLDAEMON_SERVICE_CMD start

count_actions(){
    sqlite3 /tmp/test_db.sqlite "select * from actions;" | wc -l
}

ACTION_COUNT1=`count_actions`
sleep 3
$DQLDAEMON_SERVICE_CMD status | grep -q "is running as"
ACTION_COUNT2=`count_actions`

if ! [ $ACTION_COUNT2 -gt $ACTION_COUNT1 ]; then
    echo "Error: DQLDaemon is not sending out actions."
    exit 1
fi

$DQLDAEMON_SERVICE_CMD stop
_check 10 grep -q "DQLDaemon stopped" /tmp/test_dqldaemon_log.txt
$INTFDAEMON_SERVICE_CMD stop
$DQLDAEMON_SERVICE_CMD status | grep -q "not running"

trap "" EXIT
echo $0 PASS
