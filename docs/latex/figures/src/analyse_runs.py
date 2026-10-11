#!/usr/bin/env python3
"""Turns the recorded mission runs into the numbers and plot files of the report.

  python3 analyse_runs.py            (run from anywhere, reads ../../data/runs)

Prints one line per run and the totals, and writes into ../../data:
  runs.csv           one row per run
  picks.csv          one row per pick: where the robot stood when the jaws closed
  drops.csv          one row per delivered coin: offset from the centre of its square
  track_<run>.dat    true path of a run, for the arena figure
  slam_<run>.dat     localisation error against time
"""
import csv
import math
import statistics
import sys
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent.parent / 'data'
RUNS = DATA / 'runs'

ARRAY_AHEAD = 0.0481          # m, IR array ahead of base_footprint
BAY_XS = (1.5, 2.0, 2.5)
CROSSBAR_Y = 1.45
ZONE_X = 3.0
ZONE_YS = (0.7, 0.2, -0.3)
COLOUR = {'R': 'red', 'G': 'green', 'B': 'blue'}

# Entry line: straight, arc about (0.15, 0.6), arc about (1.1892, 0), straight at y = 0.6
R = 0.6
C1 = (0.15, 0.6)
C2 = (0.15 + 2 * R * math.sin(math.pi / 3), 0.0)
JOIN_X = 0.15 + R * math.sin(math.pi / 3)


def line_distance(x, y):
    """Signed distance of a point from the entry line, positive to the left of travel."""
    if x < 0.15:
        return y
    if x < JOIN_X:
        return R - math.hypot(x - C1[0], y - C1[1])
    if x < C2[0]:
        return math.hypot(x - C2[0], y - C2[1]) - R
    return y - 0.6


def wrap(angle):
    return (angle + math.pi) % (2 * math.pi) - math.pi


def rms(values):
    return math.sqrt(sum(v * v for v in values) / len(values)) if values else math.nan


def percentile(values, q):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(q * len(ordered)))] if ordered else math.nan


def read_csv(path):
    with open(path) as stream:
        return list(csv.DictReader(stream))


def analyse(run):
    config = dict(item.split('=') for item in (run / 'config.txt').read_text().split('\n')[0].split())
    track = [{k: float(v) for k, v in row.items()} for row in read_csv(run / 'track.csv')]
    events = read_csv(run / 'events.csv')
    log = (run / 'launch.log').read_text(errors='replace')

    states = [(float(e['t']), e['text']) for e in events if e['kind'] == 'state']
    final = states[-1][1] if states else 'NONE'
    start = next(row['t'] for row in track if math.hypot(row['x'], row['y']) > 0.002)
    t_survey = next((t for t, s in states if s == 'SURVEY_DROP_ZONES'), math.nan)
    t_first_pick = next((t for t, s in states if s == 'PICK'), math.nan)
    t_end = states[-1][0] if final in ('DONE', 'FAILED') else math.nan

    # Entry line: array centre against the painted line
    entry = [row for row in track if start <= row['t'] <= t_survey]
    cross = [line_distance(row['x'] + ARRAY_AHEAD * math.cos(row['yaw']),
                           row['y'] + ARRAY_AHEAD * math.sin(row['yaw'])) for row in entry]
    stop = entry[-1] if entry else None

    # Localisation: SLAM pose against the truth, once the robot is in the room
    slam = [(row['t'], math.hypot(row['map_x'] - row['x'], row['map_y'] - row['y']),
             abs(wrap(row['map_yaw'] - row['yaw'])),
             math.hypot(row['odom_x'] - row['x'], row['odom_y'] - row['y']))
            for row in track if not math.isnan(row['map_x']) and row['t'] >= t_survey]
    odom = [math.hypot(row['odom_x'] - row['x'], row['odom_y'] - row['y'])
            for row in track if not math.isnan(row['odom_x']) and row['t'] >= t_survey]

    path = sum(math.hypot(b['x'] - a['x'], b['y'] - a['y']) for a, b in zip(track, track[1:]))

    # Picks: pose when the jaws close inside a PICK state
    picks = []
    state = None
    for event in events:
        if event['kind'] == 'state':
            state = event['text']
        elif event['kind'] == 'gripper' and state == 'PICK' and float(event['text']) > 0:
            x, y, yaw = float(event['x']), float(event['y']), float(event['yaw'])
            if y < 1.3:
                continue        # jaws closed after a failed approach, not at a crossbar
            bay = min(BAY_XS, key=lambda b: abs(b - x))
            ax = x + ARRAY_AHEAD * math.cos(yaw)
            ay = y + ARRAY_AHEAD * math.sin(yaw)
            picks.append({'run': run.name, 'bay': BAY_XS.index(bay) + 1,
                          'lateral_mm': 1000 * (ax - bay), 'along_mm': 1000 * (ay - CROSSBAR_Y),
                          'heading_deg': math.degrees(wrap(yaw - math.pi / 2))})

    # Drops: where each coin ended relative to the centre of its square
    drops = []
    home = 0
    target = {COLOUR[c]: y for c, y in zip(config['drop_order'], ZONE_YS)}
    coins_file = run / 'coins.csv'
    if coins_file.exists():
        for row in read_csv(coins_file):
            colour = row['coin'][len('coin_'):]
            dx, dy = float(row['x']) - ZONE_X, float(row['y']) - target[colour]
            inside = abs(dx) <= 0.125 and abs(dy) <= 0.125
            home += inside
            if inside:
                drops.append({'run': run.name, 'colour': colour,
                              'dx_mm': 1000 * dx, 'dy_mm': 1000 * dy})

    summary = {
        'run': run.name, 'pick': config['pick_order'], 'drop': config['drop_order'],
        'obstacles': config['obstacles'], 'state': final, 'home': home,
        'verdict': 'PASS' if 'Referee verdict: PASS' in log else
                   ('FAIL' if 'Referee verdict: FAIL' in log else 'NONE'),
        't_line': t_survey - start, 't_survey': t_first_pick - t_survey,
        't_coins': t_end - t_first_pick, 't_total': t_end - start, 'path_m': path,
        'line_rms_mm': 1000 * rms(cross), 'line_max_mm': 1000 * max(map(abs, cross), default=math.nan),
        'square_x': stop['x'] + ARRAY_AHEAD * math.cos(stop['yaw']) if stop else math.nan,
        'slam_rms_mm': 1000 * rms([e for _, e, _, _ in slam]),
        'slam_p95_mm': 1000 * percentile([e for _, e, _, _ in slam], 0.95),
        'slam_max_mm': 1000 * max((e for _, e, _, _ in slam), default=math.nan),
        'slam_yaw_rms_deg': math.degrees(rms([a for _, _, a, _ in slam])),
        'odom_end_mm': 1000 * odom[-1] if odom else math.nan,
        'odom_max_mm': 1000 * max(odom, default=math.nan),
        'retries': log.count('no marker found') + log.count('navigation failed'),
        'qr_misses': log.count('QR not read') + log.count('nothing picked'),
        'recoveries': log.count('Running spin') + log.count('Running wait'),
    }

    with open(DATA / f'track_{run.name}.dat', 'w') as out:
        for row in track[::3]:
            out.write(f"{row['x']:.3f} {row['y']:.3f}\n")
    with open(DATA / f'slam_{run.name}.dat', 'w') as out:
        out.write('t err_mm yaw_deg odom_mm\n')
        for t, err, yaw, odom_err in slam[::5]:
            out.write(f'{t - start:.1f} {1000 * err:.1f} {math.degrees(yaw):.2f} {1000 * odom_err:.1f}\n')
    return summary, picks, drops


def write_rows(path, rows):
    if not rows:
        return
    with open(path, 'w', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: f'{v:.2f}' if isinstance(v, float) else v for k, v in row.items()})


def main():
    names = sys.argv[1:] or sorted(p.name for p in RUNS.iterdir() if p.name.startswith('m'))
    summaries, picks, drops = [], [], []
    for name in names:
        run = RUNS / name
        if not (run / 'coins.csv').exists():
            print(f'{name}: not finished, skipped')
            continue
        summary, run_picks, run_drops = analyse(run)
        summaries.append(summary)
        picks += run_picks
        drops += run_drops
        print(' '.join(f'{k}={v:.1f}' if isinstance(v, float) else f'{k}={v}'
                       for k, v in summary.items()))
    write_rows(DATA / 'runs.csv', summaries)
    write_rows(DATA / 'picks.csv', picks)
    write_rows(DATA / 'drops.csv', drops)

    def spread(key, rows=summaries):
        values = [row[key] for row in rows if not math.isnan(row[key])]
        return (f'{key}: mean {statistics.mean(values):.1f} min {min(values):.1f} '
                f'max {max(values):.1f} n {len(values)}')

    print()
    print('runs', len(summaries), 'pass', sum(s['verdict'] == 'PASS' for s in summaries),
          'coins home', sum(s['home'] for s in summaries), 'of', 3 * len(summaries))
    for key in ('t_line', 't_survey', 't_coins', 't_total', 'path_m', 'line_rms_mm', 'line_max_mm',
                'square_x', 'slam_rms_mm', 'slam_p95_mm', 'slam_max_mm', 'slam_yaw_rms_deg',
                'odom_end_mm', 'odom_max_mm'):
        print(spread(key))
    for key in ('lateral_mm', 'along_mm', 'heading_deg'):
        print('pick', spread(key, picks), 'rms', f'{rms([p[key] for p in picks]):.1f}')
    for key in ('dx_mm', 'dy_mm'):
        print('drop', spread(key, drops), 'rms', f'{rms([d[key] for d in drops]):.1f}')
    radial = [math.hypot(d['dx_mm'], d['dy_mm']) for d in drops]
    if radial:
        print(f'drop radial: mean {statistics.mean(radial):.1f} max {max(radial):.1f} n {len(radial)}')


if __name__ == '__main__':
    main()
