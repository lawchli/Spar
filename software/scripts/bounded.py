#!/usr/bin/env python3
"""Portable timeout; terminates its process group, also when interrupted."""
import os
import signal
import subprocess
import sys

p = subprocess.Popen(sys.argv[2:], start_new_session=True)
def stop(*_):
    if p.poll() is None:
        os.killpg(p.pid, signal.SIGTERM)
        try:
            p.wait(timeout=2)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            p.wait()
for sig in (signal.SIGINT, signal.SIGTERM):
    signal.signal(sig, lambda *_: (stop(), sys.exit(130)))
try:
    sys.exit(p.wait(timeout=float(sys.argv[1])))
except subprocess.TimeoutExpired:
    stop()
    sys.exit(124)
