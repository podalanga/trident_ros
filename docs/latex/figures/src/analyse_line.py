#!/usr/bin/env python3
"""Cross-track error of the IR array on the entry line, for the runs of run_line_sweep.sh.

Prints one line per run and writes ../../data/line.csv and one track file per run.
"""
import csv
import math
import re
from pathlib import Path

from analyse_runs import ARRAY_AHEAD, DATA, line_distance, rms

rows = []
for run in sorted((DATA / 'line').iterdir()):
    noise, speed = re.match(r'n([\d.]+)_v([\d.]+)', run.name).groups()
    with open(run / 'track.csv') as stream:
        track = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(stream)]
    moving = [row for row in track if 0.01 < row['x']]
    # Drop the samples after the stop
    end = max(range(len(moving)), key=lambda i: moving[i]['x'])
    moving = moving[:end + 1]
    cross = [line_distance(row['x'] + ARRAY_AHEAD * math.cos(row['yaw']),
                           row['y'] + ARRAY_AHEAD * math.sin(row['yaw'])) for row in moving]
    result = (run / 'result.txt').read_text()
    reached = 'reached_marker=True' in result.replace(' ', '') or 'reached_marker: true' in result
    last = moving[-1]
    row = {'noise_V': float(noise), 'speed': float(speed), 'reached': int(reached),
           'rms_mm': 1000 * rms(cross), 'max_mm': 1000 * max(map(abs, cross)),
           'time_s': last['t'] - moving[0]['t'],
           'array_stop_x': last['x'] + ARRAY_AHEAD * math.cos(last['yaw']),
           'stop_y': last['y']}
    rows.append(row)
    print(' '.join(f'{k}={v:.3f}' if isinstance(v, float) else f'{k}={v}' for k, v in row.items()))
    with open(DATA / f'line_{run.name}.dat', 'w') as out:
        out.write('x err_mm\n')
        for sample, value in zip(moving[::2], cross[::2]):
            out.write(f"{sample['x']:.3f} {1000 * value:.2f}\n")

with open(DATA / 'line.csv', 'w', newline='') as stream:
    writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
    writer.writeheader()
    for row in rows:
        writer.writerow({k: f'{v:.3f}' if isinstance(v, float) else v for k, v in row.items()})
