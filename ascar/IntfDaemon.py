#!/usr/bin/env python

"""ASCAR Interface Daemon"""

# Import system modules
from copy import *
import pickle
import time
from typing import List
import zlib
import zmq
# Import local modules
from .ReplayDB import *
from .ascar_logging import *
from . import LustreCommon

__author__ = 'Yan Li'
__copyright__ = 'Copyright (c) 2016, 2017 The Regents of the University of California. All rights reserved.'


class IntfDaemon:
    """The Interface Daemon

    This daemon's public methods are thread-safe.

    :type nodeid_map: dict
    :type opt: dict
    """
    _abort_inproc_addr = 'inproc://#intfdaemonabrt'
    abort_publisher_socket = None
    abort_subscriber_socket = None
    ma_status = dict()
    nodeid_map = None
    opt = None
    prev_health_status = ''
    started = False
    socket = None

    def __init__(self, opt: dict, store_action=True):
        """
        :param opt:
        :param store_action: Whether broadcast action should be stored in DB. Used in testing.
        """
        self.opt = deepcopy(opt)
        if 'nodeid_map' in opt:
            self.nodeid_map = opt['nodeid_map']
        if 'intf_daemon_loc' in opt.keys():
            self.port = int(opt['intf_daemon_loc'].split(':')[1])
        else:
            self.port = 9123
        self.store_action = store_action

    def _health_check(self) -> str:
        if not self.nodeid_map:
            result = 'nodeid_map is missing; '
            # just return the known MAs
            for ma in self.ma_status:
                result += '{ma}: ok; '.format(ma=ma)
            return result

        result = ''
        ok_nodes = 0
        unresponsive_nodes = 0
        for ma in self.nodeid_map.values():
            if ma not in self.ma_status:
                result += '{ma}: not seen; '.format(ma=ma)
            elif abs(time.time() - self.ma_status[ma]) < 20:
                result += '{ma}: ok; '.format(ma=ma)
                ok_nodes += 1
            else:
                result += '{ma}: unresponsive, last seen at {time}; '.format(ma=ma, time=self.ma_status[ma])
                unresponsive_nodes += 1
        if unresponsive_nodes != 0:
            err = 'MA went unresponsive: ' + result
            logger.error(err)
            raise RuntimeError(err)
        if ok_nodes == len(self.nodeid_map):
            result = 'All MA healthy. ' + result
        return result

    def _handle_status(self, caller):
        """Handle the status query command

        Check if all MAs are alive

        :param caller: identity of the caller
        """
        self.socket.send(caller, zmq.SNDMORE)
        self.socket.send(self._health_check())

    def _broadcast(self, req: List):
        """Broadcast actions or heartbeats to all MAs

        This function should only be called internally and is not thread-safe

        :return:
        """
        for ma in self.ma_status:
            logger.debug('Sending to MA {ma}'.format(ma=ma))
            self._send_to_ma(ma, req)

    def _send_to_ma(self, ma, obj):
        """Send pickled obj to MA

        self.socket must NOT be busy.
        """
        self.socket.send(str(ma).encode('ascii'), zmq.SNDMORE)
        self.socket.send(zlib.compress(pickle.dumps(obj)))

    # Anecdotal evidence suggests that 127.0.0.1 works but localhost doesn't:
    # https://stackoverflow.com/questions/21759094/pyzmq-push-socket-does-not-block-on-send#comment33001703_21766554
    @staticmethod
    def broadcast_action(action, intf_daemon_loc: str = 'tcp://127.0.0.1:9123'):
        """Broadcast action to all connected MAs

        This function is thread-safe

        :param action: The action to broadcast. The first element should be the action that
                       will be saved to DB. The rest of the list is complementary data that
                       will be sent to CAs but not stored in DB.
        :param intf_daemon_loc:
        """
        assert isinstance(action[0], int)
        context = zmq.Context()
        s = context.socket(zmq.DEALER)
        s.setsockopt(zmq.IDENTITY, '-1'.encode('ascii'))
        s.connect(intf_daemon_loc)
        data = [LustreCommon.protocol_ver, int(time.time()), b'ACTION'] + action
        s.send(zlib.compress(pickle.dumps(data)))

    def start(self):
        """Starts the Interface Daemon and listens on the port
        """
        assert not self.socket, 'Server already started.'
        # ReplayDB must be created in start(), which may be run in a separate thread.
        # SQLite doesn't like the DBConn be created in different threads.
        db = ReplayDB(self.opt)

        context = zmq.Context()
        self.socket = context.socket(zmq.ROUTER)
        self.socket.set_hwm(5000)
        self.socket.bind('tcp://*:{port}'.format(port=self.port))
        logger.info('Listening on port {port}'.format(port=self.port))

        self.abort_publisher_socket = context.socket(zmq.PUSH)
        self.abort_publisher_socket.bind(self._abort_inproc_addr)

        self.abort_subscriber_socket = context.socket(zmq.PULL)
        self.abort_subscriber_socket.connect(self._abort_inproc_addr)

        poller = zmq.Poller()
        poller.register(self.socket, zmq.POLLIN)
        poller.register(self.abort_subscriber_socket, zmq.POLLIN)

        heartbeat_ts = time.time()
        while True:
            flush_log()
            p = dict(poller.poll(1000))
            if self.socket in p:
                ma_id = int(self.socket.recv())
                req = pickle.loads(zlib.decompress(self.socket.recv()))
                logger.debug('From {ma_id} received {data}'.format(ma_id=ma_id, data=str(req)))
                assert req[0] == LustreCommon.protocol_ver
                ts = req[1]
                # the data payload maybe an empty list
                if len(req) >= 3 and isinstance(req[2], bytes):
                    # this is a command, not data
                    cmd = req[2]
                    if cmd == b'STATUS':
                        self._handle_status(ma_id)
                    elif cmd == b'ACTION':
                        action = req[3:]
                        if self.store_action:
                            db.insert_action(int(time.time()), action[0])
                        logger.info('Broadcasting action {0}'.format(action[0]))
                        self._broadcast(req)
                        # Sending action is also a kind of heartbeat
                        heartbeat_ts = time.time()
                    else:
                        logger.warning('Unknown command received: ' + cmd)
                else:
                    self.ma_status[ma_id] = ts
                    db.insert_pi(ma_id, int(ts), req[2:])
            elif self.abort_subscriber_socket in p:
                logger.debug('IntfDaemon stopped')
                self.socket.close()
                break

            # Use 0.9 here so we would still send out heartbeat if poll took something like 0.98 seconds
            if time.time() - heartbeat_ts > 0.9:
                logger.debug('Broadcasting heartbeat')
                self._broadcast([LustreCommon.protocol_ver, time.time(), b'HB'])
                heartbeat_ts = time.time()

            # health check
            health_status = self._health_check()
            if health_status != self.prev_health_status:
                logger.info(health_status)
                self.prev_health_status = health_status

    def stop(self):
        """Stop the daemon

        This function is thread-safe
        """
        assert self.socket
        assert self.abort_publisher_socket
        assert self.abort_subscriber_socket

        self.abort_publisher_socket.send(b'STOP')
