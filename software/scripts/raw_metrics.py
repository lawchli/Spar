#!/usr/bin/env python3
"""Metrics for vcap raw captures (S16_LE interleaved), no third-party dependencies.

Per channel: RMS / peak dBFS, and a Hann-windowed Goertzel scan that reports the
strongest tone in a band (default 1-6 kHz) and how far it stands above the band
median. A self-oscillating sidetone loop shows up as a tone with large prominence.
"""
import argparse
import array
import json
import math
import sys


def load(path, channels):
    data = array.array('h')
    with open(path, 'rb') as f:
        data.frombytes(f.read())
    if sys.byteorder != 'little':
        data.byteswap()
    frames = len(data) // channels
    return [data[c::channels][:frames] for c in range(channels)]


def tone_scan(x, rate, lo, hi, step, window, seconds):
    # Hann segments of `window` s with power averaged over `seconds` (Welch).
    # Keep window <= 1/(2*step) so a tone between scan points loses < 1.5 dB.
    n = int(window * rate)
    count = max(1, min(len(x) // n, int(seconds / window)))
    first = (len(x) - count * n) // 2
    w = [0.5 - 0.5 * math.cos(2 * math.pi * i / (n - 1)) for i in range(n)]
    segs = [[x[first + k * n + i] / 32768.0 * w[i] for i in range(n)] for k in range(count)]
    norm = sum(w) / 2
    out = []
    f = lo
    while f <= hi:
        coeff = 2 * math.cos(2 * math.pi * f / rate)
        power = 0.0
        for seg in segs:
            s1 = s2 = 0.0
            for v in seg:
                s1, s2 = v + coeff * s1 - s2, s1
            power += max(0.0, s1 * s1 + s2 * s2 - coeff * s1 * s2)
        mag = math.sqrt(power / count) / norm
        out.append((f, 20 * math.log10(mag) if mag > 0 else -200.0))
        f += step
    return out


def analyze(path, channels, rate, lo, hi, step, window, seconds, skip):
    result = []
    for x in load(path, channels):
        x = x[int(skip * rate):]
        n = len(x)
        if not n:
            result.append(None)
            continue
        sq = sum(v * v for v in x)
        mean = sum(x) / n
        rms = math.sqrt(max(0.0, sq / n - mean * mean)) / 32768
        peak = max(abs(v) for v in x) / 32768
        scan = tone_scan(x, rate, lo, hi, step, window, seconds)
        levels = sorted(db for _, db in scan)
        f_max, db_max = max(scan, key=lambda t: t[1])
        median = levels[len(levels) // 2]
        result.append({'rms_dbfs': round(20 * math.log10(rms), 1) if rms else None,
                       'peak_dbfs': round(20 * math.log10(peak), 1) if peak else None,
                       'tone_hz': f_max, 'tone_dbfs': round(db_max, 1),
                       'tone_prominence_db': round(db_max - median, 1)})
    return {'path': path, 'seconds': round(len(load(path, channels)[0]) / rate, 2), 'channels': result}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('raw', nargs='+')
    p.add_argument('--channels', type=int, default=2)
    p.add_argument('--rate', type=int, default=48000)
    p.add_argument('--lo', type=float, default=1000)
    p.add_argument('--hi', type=float, default=6000)
    p.add_argument('--step', type=float, default=25)
    p.add_argument('--window', type=float, default=0.02, help='tone scan segment length, s')
    p.add_argument('--seconds', type=float, default=1.0, help='seconds averaged for the tone scan')
    p.add_argument('--skip', type=float, default=0.5, help='seconds dropped at the start (pop / settling)')
    p.add_argument('--json', action='store_true')
    a = p.parse_args()
    for path in a.raw:
        r = analyze(path, a.channels, a.rate, a.lo, a.hi, a.step, a.window, a.seconds, a.skip)
        if a.json:
            print(json.dumps(r))
            continue
        cols = []
        for name, c in zip('LR', r['channels']):
            cols.append(f"{name}: rms {c['rms_dbfs']} pk {c['peak_dbfs']} tone {c['tone_hz']:.0f} Hz "
                        f"{c['tone_dbfs']} (+{c['tone_prominence_db']})" if c else f'{name}: empty')
        print(f"{path.rsplit('/', 1)[-1]} {r['seconds']}s  " + '  '.join(cols))
