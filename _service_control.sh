#!/bin/bash
# Testing the Interface Daemon
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
if [ -n "${VENV:-}" ]; then
    # virtualenv needs PS1
    PS1=1
    . "$VENV"
fi

if [ $# -lt 3 ]; then
    cat <<EOF
Usage: $0 module conffile <start|stop|status>
EOF
    exit 2
fi

MODULE=$1
CONFFILE=$2
CMD=$3

PIDFILE_DIR=`grep pidfile_dir $CONFFILE | cut -d"'" -f 4`
if [ -z "$PIDFILE_DIR" ]; then
    PIDFILE_DIR=/var/run
fi
PIDFILE=${PIDFILE_DIR}/${MODULE}.pid

if [ "$CMD" = "start" ]; then
    python _run_as_service.py "$1" "$2"
elif [ "$CMD" = "stop" ]; then
    if [ ! -e $PIDFILE ]; then
        echo "$PIDFILE doesn't exist. Can't find the running process."
        exit 3
    fi
    kill -TERM `cat $PIDFILE`
elif [ "$CMD" = "status" ]; then
    if [ -e $PIDFILE ]; then
        PID=`cat $PIDFILE`
        if ps -ef | grep -v grep | grep -q " ${PID} "; then
            echo "$1 is running as `cat $PIDFILE`"
        else
            rm "$PIDFILE"
            echo "$1 is not running"
        fi
    else
        echo "$1 is not running"
    fi
else
    echo "${CMD}: unknown command"
    exit 255
fi
