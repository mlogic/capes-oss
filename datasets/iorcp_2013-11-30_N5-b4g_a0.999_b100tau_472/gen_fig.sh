#!/bin/bash
set -e -u
cd `dirname $0`

DST=seth_stat.pdf
./plot_obd_stat.py iorcp_2013-11-28_07-11-54_MPIIO_w_N5_d0_i1_s1_F_b4g_t256m_s1_stat_log/seth.stat_log $DST

open $DST
