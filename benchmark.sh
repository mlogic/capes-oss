#!/bin/bash
set -e -u
cd `dirname $0`

PYTHONPATH=`pwd` time python -m cProfile -s 'cumtime' tests/benchmark_dql.py
