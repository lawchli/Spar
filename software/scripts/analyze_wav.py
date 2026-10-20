#!/usr/bin/env python3
"""Integer PCM WAV per-channel metrics, streaming, no third-party dependencies."""
import argparse
import json
import math
import wave

def analyze(path, start=0, seconds=None):
    with wave.open(str(path), 'rb') as w:
        channels, width, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        if width not in (1, 2, 3, 4) or w.getcomptype() != 'NONE':
            raise ValueError('Only integer PCM WAV supported')
        if start < 0 or (seconds is not None and seconds <= 0):
            raise ValueError('Invalid time window')
        offset = min(frames, int(start*rate))
        w.setpos(offset)
        remaining = frames-offset if seconds is None else min(frames-offset, int(seconds*rate))
        accum = [[0, 0, 0, 0, 0] for _ in range(channels)]
        scale = 2**(width*8-1)
        while remaining:
            raw = w.readframes(min(remaining, 32768))
            count = len(raw)//(channels*width)
            if not count:
                break
            remaining -= count
            for i in range(count*channels):
                b = raw[i*width:(i+1)*width]
                x = b[0]-128 if width == 1 else int.from_bytes(b, 'little', signed=True)
                s = accum[i % channels]
                s[0] += 1; s[1] += x; s[2] += x*x; s[3] = max(s[3], abs(x)); s[4] += (x <= -scale or x >= scale-1)
        result = []
        for n, total, sq, peak, clipped in accum:
            mean = total/n/scale if n else 0
            rms = math.sqrt(sq/n)/scale if n else 0
            ac = math.sqrt(max(0, rms*rms-mean*mean))
            result.append({'samples': n, 'rms': rms, 'rms_dbfs': 20*math.log10(rms) if rms else None,
                           'ac_rms': ac, 'dc_offset_fs': mean, 'peak_fs': peak/scale,
                           'rail_sample_fraction': clipped/n if n else 0})
        return {'path': str(path), 'duration_seconds': frames/rate, 'sample_rate': rate, 'channels': channels,
                'bits': width*8, 'window_start_seconds': start, 'window_seconds': seconds, 'metrics': result,
                'note': 'Rail samples suggest clipping; analogue clipping below rails is not detected. RMS alone cannot prove origin.'}
if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('wav'); p.add_argument('--start', type=float, default=0); p.add_argument('--seconds', type=float)
    a = p.parse_args()
    print(json.dumps(analyze(a.wav, a.start, a.seconds), indent=2))
