#!/usr/bin/env python

"""ASCAR Agents Common Routines Protocol

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
"""

from .ascar_logging import *
import glob
import os
import re
from typing import Dict

__author__ = 'Yan Li'
__copyright__ = 'Copyright (c) 2016, 2017 The Regents of the University of California. All rights reserved.'

protocol_ver = 1


def extract_ack_ewma_from_import(import_data: str) -> float:
    return float(re.search('(?<=ack_ewma: )[0-9.]+', import_data).group(0))


def extract_sent_ewma_from_import(import_data: str) -> float:
    return float(re.search('(?<=sent_ewma: )[0-9.]+', import_data).group(0))


def extract_rtt_ratio100_from_import(import_data: str) -> float:
    return float(re.search('(?<=rtt_ratio100: )[0-9.]+', import_data).group(0))


def extract_read_bandwidth_from_import(import_data: str) -> float:
    return float(re.search('(?<=read_throughput: )[0-9.]+', import_data).group(0))


def extract_write_bandwidth_from_import(import_data: str) -> float:
    return float(re.search('(?<=write_throughput: )[0-9.]+', import_data).group(0))


def gen_rule(rule_template: str, kv: Dict[str, float]) -> str:
    result = rule_template
    for key, val in kv.items():
        result = result.replace('{{{{ {key} }}}}'.format(key=key), str(val))
    return result


def read_proc_file(filename: str) -> float:
    """Read one number from 'osc_path/filename'
    """
    with open(filename, 'rt') as procfile:
        try:
            # Don't use readline() because it can cause out-of-memory error when reading a bizarre procfile
            return float(procfile.read(100))
        except (OSError, ValueError) as e:
            logging.error('{type}: {msg}'.format(type=type(e).__name__, msg=str(e)))
            return 0


def set_procfs_osc(filename: str, data: int, num_osc: int) -> None:
    control_files = glob.glob('/proc/fs/lustre/osc/*/' + filename)
    assert len(control_files) == num_osc

    for cf in control_files:
        with open(cf, 'w') as fh:
            fh.write(str(data))


def set_mrif(mrif: int, num_osc: int) -> None:
    set_procfs_osc('max_rpcs_in_flight', mrif, num_osc)
    # set_procfs_osc('max_dirty_mb', min(256, 4 * mrif), num_osc)


def set_rule(rule: str, num_osc: int) -> None:
    rule_files = glob.glob('/proc/fs/lustre/osc/*/qos_rules')
    assert len(rule_files) == num_osc
    for rule_file in rule_files:
        with open(rule_file, 'w') as fh:
            fh.write(rule)
