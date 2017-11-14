import atexit
import logging
import logging.handlers

__author__ = 'Yan Li'
__copyright__ = 'Copyright (c) 2016, 2017 The Regents of the University of California. All rights reserved.'
__license__ = 'BSD 3-clause'

logger = logging.getLogger('ASCAR')
FORMAT = "[%(asctime)s - %(filename)s:%(lineno)s - %(funcName)10s() ] %(message)s"
log_handler = None    # type: logging.FileHandler
memory_handler = None


def add_log_file(filename: str, lazy_flush=False):
    global log_handler
    global memory_handler
    if memory_handler:
        raise RuntimeError('log file has already been set')

    formatter = logging.Formatter(FORMAT)
    log_handler = logging.FileHandler(filename)
    log_handler.setFormatter(formatter)

    memory_handler = logging.handlers.MemoryHandler(
        capacity=1024 * 100,
        flushLevel=logging.ERROR if lazy_flush else logging.DEBUG,
        target=log_handler
    )

    logger.addHandler(memory_handler)


def flush_log():
    if memory_handler:
        memory_handler.flush()
atexit.register(flush_log)


def set_log_level(level: int) -> None:
    if not logger.hasHandlers():
        logging.basicConfig(format=FORMAT)
    logger.setLevel(level)
