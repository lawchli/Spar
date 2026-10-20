#!/usr/bin/env python3
"""Concurrent passive MBHC/framework observation. No app starts or mixer writes."""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import signal
import subprocess
import threading

ap = argparse.ArgumentParser()
ap.add_argument('--out', required=True)
ap.add_argument('--seconds', type=float, default=120)
ap.add_argument('--interval', type=float, default=2)
a = ap.parse_args()
if a.seconds <= 0 or a.interval < 0.5:
    ap.error('seconds > 0 and interval >= 0.5 required')
out = Path(a.out)
base = [os.environ['ADB'], '-s', os.environ['ANDROID_SERIAL']]
stop = threading.Event()
procs = []
lock = threading.Lock()
def stamp():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec='milliseconds')
def argv(command):
    # Pass the script as one su -c argument. Extra quotes become part of the
    # command name under Magisk (sh: "getevent -lt": not found).
    return base + ['exec-out', 'su', '-c', command]
def sample(command):
    try:
        r = subprocess.run(argv(command), capture_output=True, timeout=15)
        return {'exit': r.returncode, 'stdout': r.stdout.decode(errors='replace'), 'stderr': r.stderr.decode(errors='replace')}
    except subprocess.TimeoutExpired:
        return {'exit': 124, 'stderr': 'timeout'}
def stream(name, command):
    with (out/name).open('w', buffering=1) as f:
        p = subprocess.Popen(argv(command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, errors='replace', start_new_session=True)
        with lock:
            procs.append(p)
        for line in p.stdout:
            f.write(f'{stamp()} {line}')
            if stop.is_set():
                break
        f.write(f'{stamp()} STREAM_END exit={p.poll()}\n')
def poll(name, command, interval):
    with (out/name).open('w', buffering=1) as f:
        while not stop.is_set():
            begin = stamp()
            result = sample(command)
            f.write(json.dumps({'host_begin_utc': begin, 'host_end_utc': stamp(), **result})+'\n')
            stop.wait(interval)
for sig in (signal.SIGTERM, signal.SIGINT):
    signal.signal(sig, lambda *_: stop.set())
metadata = {'host_start_utc': stamp(), 'serial': os.environ['ANDROID_SERIAL'], 'seconds': a.seconds,
            'note': 'Host receive timestamps; getevent has device monotonic time. Dumps are not atomic.',
            'clock_alignment': sample("date -u; cat /proc/uptime"),
            'input_map': sample('getevent -lp; cat /proc/bus/input/devices')}
(out/'metadata.json').write_text(json.dumps(metadata, indent=2))
sysfs = (Path(os.environ['ROOT'])/'scripts/sysfs-state.sh').read_text()
tasks = [
    (stream, ('getevent.log', 'getevent -lt')),
    (stream, ('logcat.log', 'logcat -b all -v epoch -T 1')),
    (poll, ('policy.jsonl', 'date -u; cat /proc/uptime; dumpsys media.audio_policy', a.interval)),
    (poll, ('audio-service.jsonl', 'date -u; cat /proc/uptime; dumpsys audio', a.interval)),
    (poll, ('sysfs.jsonl', sysfs, a.interval)),
    (poll, ('kernel.jsonl', 'dmesg', max(10, a.interval))),
]
threads = [threading.Thread(target=fn, args=args, daemon=True) for fn, args in tasks]
try:
    for t in threads:
        t.start()
    print(f'Watching for {a.seconds:g}s: {out}; Ctrl-C stops. No recording app started.', flush=True)
    stop.wait(a.seconds)
finally:
    stop.set()
    with lock:
        active = list(procs)
    for p in active:
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGTERM)
    for p in active:
        try:
            p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
    for t in threads:
        t.join(timeout=16)
    (out/'end.json').write_text(json.dumps({'host_end_utc': stamp(), 'clock_alignment': sample('date -u; cat /proc/uptime')}))
