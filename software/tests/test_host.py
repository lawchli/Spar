#!/usr/bin/env python3
"""Host tests use synthetic ADB data, NEVER a physical device."""
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import wave

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('metrics', ROOT/'scripts/analyze_wav.py')
metrics = importlib.util.module_from_spec(spec); spec.loader.exec_module(metrics)

FAKE_ADB = r"""#!/usr/bin/env python3
import os,sys,time,shlex
args=sys.argv[1:]
if args[:1] == ['-s']: args=args[2:]
if args == ['devices']:
    print('List of devices attached\nMOCK_ONLY\tdevice'); sys.exit(0)
if args == ['get-state']: print('device'); sys.exit(0)
cmd=' '.join(args)
if 'id' == args[-1]: print('uid=0(root) gid=0(root)'); sys.exit(0)
if 'find -L' in cmd:
    print('/vendor/etc/audio_policy_configuration.xml\n/vendor/etc/includes.xml'); sys.exit(0)
if 'cat /vendor/etc/audio_policy_configuration.xml' in cmd:
    print('<audioPolicyConfiguration xmlns:xi="http://www.w3.org/2001/XInclude"><xi:include href="includes.xml"/><devicePort tagName="Wired Headset Mic"/></audioPolicyConfiguration>'); sys.exit(0)
if 'cat /vendor/etc/includes.xml' in cmd:
    print('<included/>'); sys.exit(0)
if args[:1] == ['exec-out'] and ('getevent -lt' in cmd or 'logcat -b all -v epoch -T 1' in cmd):
    print('[12.0] /dev/input/event7: EV_SW SW_MICROPHONE_INSERT 00000001',flush=True)
    while True: time.sleep(1)
if 'dumpsys media.audio_policy' in cmd:
    print('Available input devices:\n  AUDIO_DEVICE_IN_WIRED_HEADSET\nInputs (1):\n  Devices: AUDIO_DEVICE_IN_BUILTIN_MIC\nPatches: mock-only'); sys.exit(0)
if 'dumpsys media.audio_flinger' in cmd:
    print('mock permission error',file=sys.stderr); sys.exit(13)
if args[-1:] == ['sh']: sys.stdin.read()
print('MOCK ONLY — NOT DEVICE EVIDENCE')
"""
class HostTests(unittest.TestCase):
    def test_wav_metrics_and_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'tone.wav'
            samples = [int(8192*math.sin(2*math.pi*1000*n/48000))+1024 for n in range(48000)]
            with wave.open(str(p),'wb') as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(48000)
                w.writeframes(struct.pack('<'+'h'*len(samples),*samples))
            r = metrics.analyze(p)
            self.assertEqual(r['duration_seconds'],1)
            self.assertAlmostEqual(r['metrics'][0]['dc_offset_fs'],1024/32768,places=5)
            self.assertAlmostEqual(r['metrics'][0]['ac_rms'],0.25/math.sqrt(2),places=4)
            self.assertEqual(metrics.analyze(p,.25,.5)['metrics'][0]['samples'],24000)
    def test_stereo_clipping_and_24bit(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'rail.wav'
            with wave.open(str(p),'wb') as w:
                w.setnchannels(2); w.setsampwidth(3); w.setframerate(48000)
                w.writeframes((8388607).to_bytes(3,'little',signed=True)+(0).to_bytes(3,'little',signed=True))
            r=metrics.analyze(p)
            self.assertEqual(r['metrics'][0]['rail_sample_fraction'],1)
            self.assertEqual(r['metrics'][1]['rms'],0)
    def test_diagnose_and_watch_mock(self):
        with tempfile.TemporaryDirectory() as tmp:
            fake=Path(tmp)/'adb'; fake.write_text(FAKE_ADB); fake.chmod(0o755)
            env={**os.environ,'ADB':str(fake),'ANDROID_SERIAL':'MOCK_ONLY','XZ1_LOG_ROOT':str(Path(tmp)/'logs')}
            r=subprocess.run(['bash',str(ROOT/'diagnose.sh')],env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(r.returncode,0,r.stderr)
            snapshots=list((Path(tmp)/'logs').glob('*snapshot-*'))
            self.assertEqual(len(snapshots),1)
            out=snapshots[0]
            self.assertTrue((out/'xml/vendor/etc/includes.xml').exists())
            self.assertIn('audio-flinger\t13',(out/'status.tsv').read_text())
            self.assertIn('AUDIO_DEVICE_IN_WIRED_HEADSET',(out/'policy-excerpts.txt').read_text())
            r=subprocess.run(['bash',str(ROOT/'watch.sh'),'--seconds','1','--interval','.5'],env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(r.returncode,0,r.stderr)
            out=list((Path(tmp)/'logs').glob('*watch-*'))[0]
            self.assertIn('SW_MICROPHONE_INSERT',(out/'getevent.log').read_text())
            self.assertTrue((out/'end.json').exists())
            self.assertTrue(json.loads((out/'policy.jsonl').read_text().splitlines()[0])['host_begin_utc'])
    def test_timeout(self):
        r=subprocess.run(['python3',str(ROOT/'scripts/bounded.py'),'.1','python3','-c','import time; time.sleep(10)'])
        self.assertEqual(r.returncode,124)

if __name__ == '__main__':
    unittest.main(verbosity=2)
