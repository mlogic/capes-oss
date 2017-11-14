#!/usr/bin/env python

"""ASCAR Monitor Agent

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

import gc
import pickle
import socket
import time
import zlib
import zmq
from . import LustreCommon
from .ascar_logging import *

__author__ = 'Yan Li'
__copyright__ = 'Copyright (c) 2016, 2017 The Regents of the University of California. All rights reserved.'


class MonitorAgent:
    """
    This agent samples system performance indicators and reports them back to an :doc:`intf-daemon`

    :type collect_time_decimal: float
    :type context: zmq.Context
    """
    collectors = None
    debugging_level = 0
    id = None                        # type: int
    last_collect_second = 0
    collect_time_decimal = 0.5       # we always collect at the middle of a second
    poller = None
    socket = None
    stopped = False
    controller = None
    context = None

    def __init__(self, opt: dict):
        if 'ma_debugging_level' in opt:
            self.debugging_level = opt['ma_debugging_level']
        # We use MA_ID if it exists
        if 'ma_id' in opt:
            self.id = opt['ma_id']
        else:
            # Look it up using our hostname
            self.id = opt['nodeid_map'][socket.gethostname()]
        logger.info('MA on {hostname} created with ID {id}'.format(hostname=socket.gethostname(), id=self.id))
        self.parent_intf_daemon = opt['intf_daemon_loc']
        self.collectors = opt.get('collectors')
        self.tick_len = opt['tick_len'] if 'tick_len' in opt else 1
        self.controller = opt.get('controller')

        # don't create zmq context here because start() may be called in a different process/thread

    def send_obj(self, data):
        assert isinstance(data, list), 'Wrong data type for send_obj'

        # prefix it with the protocol version
        data = [LustreCommon.protocol_ver] + data

        if not self.socket:
            self.connect()
        self.socket.send(zlib.compress(pickle.dumps(data)))
        logger.debug('Message sent at {ts}'.format(ts=time.time()))

    def timestamp_and_send_obj(self, data, ts=None):
        assert isinstance(data, list), 'Wrong data type for timestamp_and_send_obj'

        # prefix it with the timestamp
        if not ts:
            ts = int(time.time())
        self.send_obj([ts] + data)

    def connect(self):
        if not self.context:
            self.context = zmq.Context()
        self.socket = self.context.socket(zmq.DEALER)
        self.socket.setsockopt(zmq.IDENTITY, str(self.id).encode('ascii'))
        self.socket.connect('tcp://{parent}'.format(parent=self.parent_intf_daemon))

        self.poller = zmq.Poller()
        self.poller.register(self.socket, zmq.POLLIN)

    def disconnect(self):
        if not self.socket or not self.context or not self.poller:
            raise RuntimeError('Trying to disconnect an uninitialized socket')
        self.poller.unregister(self.socket)
        del self.poller
        self.socket.close()
        del self.socket
        del self.context
        self.context = None

    def start(self):
        if self.debugging_level >= 1:
            import cProfile
            import io
            import pstats
            pr = cProfile.Profile()
            pr.enable()
        if self.debugging_level >= 2:
            from pympler.tracker import SummaryTracker
            tracker = SummaryTracker()

        # context must be created here because this function may be executed in a separate
        # process/thread
        self.connect()
        heartbeat_ts = time.time()

        # GC causes unplanned stall and disrupts precisely timed collection.
        # Disable it and do it manually before sleeping.
        gc.disable()
        try:
            logger.info('MA started')
            while not self.stopped:
                if self.collectors:
                    ts = time.time()
                    if ts - (self.last_collect_second+self.collect_time_decimal) >= self.tick_len - 0.01:
                        # This must be updated *before* collecting to prevent the send time from
                        # slowly drifting away
                        self.last_collect_second = int(ts)
                        result = []
                        for c in self.collectors:
                            result.extend(c())
                        logger.info('Collected: ' + str(result))
                        self.timestamp_and_send_obj(result, ts)
                    else:
                        pass
                else:
                    self.last_collect_second = time.time()

                gc.collect()
                flush_log()

                # Print out memory usage every minute
                if self.debugging_level >= 2 and int(time.time()) % 60 == 0:
                    print('Time: ' + time.asctime(time.localtime(time.time())))
                    tracker.print_diff()

                # Calculate the precise time for next collection
                sleep_second = self.last_collect_second + self.collect_time_decimal + self.tick_len - time.time()
                sleep_second = max(sleep_second, 0)

                sleep_start_ts = time.time()
                p = dict(self.poller.poll(sleep_second * 1000))
                logger.debug('Slept {0} seconds'.format(time.time() - sleep_start_ts))
                if self.socket in p:
                    req = pickle.loads(zlib.decompress(self.socket.recv()))
                    assert req[0] == LustreCommon.protocol_ver
                    heartbeat_ts = time.time()
                    if isinstance(req[2], bytes):
                        # this is a command, not data
                        cmd = req[2]
                        if cmd == b'ACTION':
                            action = req[3]
                            if action == 0:
                                logger.info('Received action 0, ignored')
                            else:
                                logger.info('Performing action {action}'.format(action=action))
                                self.controller(req[3:])
                        elif cmd == b'HB':
                            logger.debug('Received heartbeat')
                        else:
                            logger.warning('Unknown command received: ' + cmd)
                    else:
                        logger.error('Corrupted message received: ' + req)
                else:
                    if heartbeat_ts and time.time() - heartbeat_ts > 5:
                        # reconnect
                        self.disconnect()
                        self.connect()

                        logger.warning('Connection timeout, reconnected')
                        heartbeat_ts = time.time()

            logger.info('MA stopped')
        finally:
            gc.enable()

            if self.debugging_level >= 1:
                pr.disable()
                s = io.StringIO()
                sortby = 'cumulative'
                ps = pstats.Stats(pr, stream=s).sort_stats(sortby)
                ps.print_stats()
                print(s.getvalue())

    def stop(self):
        logger.info('Requesting MA to stop...')
        self.stopped = True
