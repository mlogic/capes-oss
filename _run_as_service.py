#!/usr/bin/env python

"""MonitorAgent as a system service

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

import ascar.ascar_logging
import daemon
import importlib.util
from lockfile.pidlockfile import PIDLockFile
import logging
import os
import signal
import sys


def check_stale_lock(pidfile):
    pidfile_pid = pidfile.read_pid()
    if pidfile_pid is not None:
        try:
            os.kill(pidfile_pid, signal.SIG_DFL)
        except ProcessLookupError as exc:
            # The specified PID does not exist
            pidfile.break_lock()
            return
        print("Process is already running")
        exit(255)
    return

if len(sys.argv) < 3:
    print('Usage: {1} ascar_module conffile'.format(sys.argv[0]))
    exit(2)

# Import the ASCAR module
class_name = sys.argv[1]

# Import the conffile
spec = importlib.util.spec_from_file_location('conf', sys.argv[2])
conf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(conf)
opt = conf.opt

# Setup ASCAR
logfile = opt[class_name + '_logfile'] if class_name + '_logfile' in opt.keys()\
          else '/var/log/{0}.log'.format(class_name)
ascar.add_log_file(logfile, opt.get('log_lazy_flush', False))
ascar.logger.setLevel(opt['loglevel'] if 'loglevel' in opt else logging.INFO)
# Create an instance of class_name
class_name_parts = class_name.split('.')
m = importlib.import_module('.'.join(class_name_parts[:-1]))
m = getattr(m, class_name_parts[-1])
app = m(conf.opt)

pidfile_name = os.path.join(opt['pidfile_dir'] if 'pidfile_dir' in opt.keys() else '/var/run',
                            class_name + '.pid')
pidfile = PIDLockFile(pidfile_name, timeout=-1)
check_stale_lock(pidfile)
context = daemon.DaemonContext(
    # working_directory='/var/lib/foo',
    pidfile=pidfile,
    stdout=open(logfile + '_stdout', 'w+'),
    stderr=open(logfile + '_stderr', 'w+'),
)


def stop(signum, frame):
    app.stop()


context.signal_map = {
    signal.SIGTERM: stop,
    signal.SIGHUP: 'terminate',
    # signal.SIGUSR1: reload_program_config,
    }

context.files_preserve = [ascar.ascar_logging.log_handler.stream]

with context:
    app.start()
