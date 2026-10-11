#!/usr/bin/env bash
# Waits for a running mission batch to end, then runs the line following sweep.
while pgrep -f run_missions.sh > /dev/null; do sleep 10; done
"$(dirname "${BASH_SOURCE[0]}")"/run_line_sweep.sh 0.0:0.10 0.05:0.10 0.2:0.10 0.5:0.10 1.0:0.10 \
    0.05:0.05 0.05:0.15 0.05:0.20 0.05:0.30 > /ws/docs/latex/data/sweep.log 2>&1
