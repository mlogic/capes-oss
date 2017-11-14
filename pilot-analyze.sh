#!/bin/bash
# PIlot analyze script
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

RESULT=$1
WARMUP_LEN=`grep "warm up len:" ${RESULT}/params | awk '{print $4}'`
TMP=`mktemp`
./plot_replay_db.py -p $RESULT/lyra/ascar_replay_db.sqlite >$TMP
TOTAL_DATA=`cat $TMP | wc -l`
WARMUP_DATA=`mktemp`
TRAINING_DATA=`mktemp`
# Filter out 0 data because they mess up with harmonic mean
cat $TMP | head -$((WARMUP_LEN + 1)) | grep -v ',0\..*' >$WARMUP_DATA
cat $TMP | tail -$((TOTAL_DATA - WARMUP_LEN - 1)) | grep -v ',0\..*' >$TRAINING_DATA

echo "Baseline"
echo "=========="
$PILOT_BIN analyze -f 1 -i 1 $WARMUP_DATA

echo "Training data"
echo "=========="
$PILOT_BIN analyze -f 1 -i 1 $TRAINING_DATA
