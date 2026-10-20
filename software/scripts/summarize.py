#!/usr/bin/env python3
"""Derived excerpts only: raw logs remain the source of truth."""
from pathlib import Path
import re
import sys
out = Path(sys.argv[1])
pattern = re.compile(r'headset|wired|mic|ANC|ANCLeft|ANCRight|External Stereo|LINE|AMIC|ADC|DEC|TX|MBHC', re.I)
paths = list(out.glob('*.txt')) + list((out/'xml').rglob('*.xml'))
with (out/'keyword-hits.txt').open('w') as f:
    for p in paths:
        if p.name.endswith('-hits.txt'):
            continue
        for i, line in enumerate(p.read_text(errors='replace').splitlines(), 1):
            if pattern.search(line):
                f.write(f'{p.relative_to(out)}:{i}:{line}\n')
policy = (out/'audio-policy.txt')
if policy.exists():
    lines = policy.read_text(errors='replace').splitlines()
    selected = set()
    for i, line in enumerate(lines):
        if re.search(r'available.*(input|device)|inputs\s*\(|patch|active|wired_headset', line, re.I):
            selected.update(range(max(0, i-2), min(len(lines), i+25)))
    (out/'policy-excerpts.txt').write_text('\n'.join(f'{i+1}: {lines[i]}' for i in sorted(selected)))
