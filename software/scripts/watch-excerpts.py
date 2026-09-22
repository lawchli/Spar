#!/usr/bin/env python3
"""Extract relevant events without promoting correlations into causes."""
from pathlib import Path
import json
import re
import sys
root = Path(sys.argv[1])
pattern = re.compile(r'SW_.*(HEADPHONE|MICROPHONE|JACK)|KEY_(MEDIA|PLAYPAUSE|VOLUME|VOICE)|h2w|wired|80000010|MBHC|XZ1MARK|XZ1Audio', re.I)
with (root/'events-excerpt.txt').open('w') as dst:
    for name in ('getevent.log', 'logcat.log'):
        p = root/name
        if p.exists():
            for line in p.read_text(errors='replace').splitlines():
                if pattern.search(line):
                    dst.write(name+': '+line+'\n')
    p = root/'policy.jsonl'
    if p.exists():
        for line in p.read_text().splitlines():
            record = json.loads(line)
            lines = record.get('stdout','').splitlines()
            dst.write('\nPOLICY SAMPLE '+record['host_begin_utc']+'\n')
            # Keep context; a declared port is not necessarily an available device.
            indexes = set()
            for n, value in enumerate(lines):
                if re.search(r'available.*input|inputs\s*\(|patch|WIRED_HEADSET', value, re.I):
                    indexes.update(range(max(0,n-2),min(len(lines),n+20)))
            for n in sorted(indexes):
                dst.write(f'{n+1}: {lines[n]}\n')
print(root/'events-excerpt.txt')
