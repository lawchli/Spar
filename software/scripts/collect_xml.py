#!/usr/bin/env python3
"""Read audio XML plus policy includes, preserving original paths and bytes."""
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

out = Path(sys.argv[1])
adb = os.environ.get('ADB')
if not adb:
    import shutil
    adb = shutil.which('adb')
serial = os.environ['ANDROID_SERIAL']
all_paths = {s.strip() for s in (out/'xml-paths.txt').read_text().splitlines() if s.startswith('/')}
pending = [p for p in all_paths if re.search(r'audio|mixer|sound|platform_info', p, re.I)]
seen = set()
errors = []
while pending:
    p = pending.pop()
    if p in seen:
        continue
    seen.add(p)
    if not re.fullmatch(r'/[A-Za-z0-9_./+@-]+', p) or '..' in Path(p).parts:
        errors.append((p, 'unsafe path skipped')); continue
    try:
        # exec-out already preserves the su -c argument; literal outer quotes
        # make Magisk try to execute a command named "cat /path".
        r = subprocess.run([adb, '-s', serial, 'exec-out', 'su', '-c', f'cat {p}'], capture_output=True, timeout=20)
        if r.returncode:
            errors.append((p, r.stderr.decode(errors='replace'))); continue
        target = out/'xml'/p.lstrip('/')
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(r.stdout)
        try:
            root = ET.fromstring(r.stdout)
            for e in root.iter():
                if e.tag.endswith('include') and e.get('href'):
                    ref = str(Path(p).parent / e.get('href'))
                    if ref in all_paths:
                        pending.append(ref)
        except ET.ParseError:
            errors.append((p, 'not parseable XML; raw retained'))
    except subprocess.TimeoutExpired:
        errors.append((p, 'read timed out'))
(out/'xml-errors.txt').write_text('\n'.join(f'{p}: {msg}' for p, msg in errors))
