# Spar software

Phone-side tools for Spar, run from a Mac or Linux host over ADB.

It started as a diagnostic kit for finding out how the phone detects a wired headset and where its microphone input is routed; the diagnostic tools only collect evidence. From v0.3 the stereo tools change the codec mixer and grab the headset input device, both temporarily and reversibly.

| Version | What it adds |
|---|---|
| v0.1 | Diagnostic kit and Probe app |
| v0.2 | Mono line input through the headset mic contact: [docs/MONO-LINE-IN.md](docs/MONO-LINE-IN.md) |
| v0.3 | Stereo capture on the 5-pole jack, with monitoring: [docs/STEREO-CAPTURE.md](docs/STEREO-CAPTURE.md) |

## Requirements

- Host: macOS (Bash 3.2 is enough) or Linux, with `adb` (Android platform-tools) and Python 3
- Phone: rooted (Magisk), USB or wireless debugging enabled
- Tested on: Sony Xperia XZ1 Compact (G8441, MSM8998 / WCD9335 "tasha" codec)

The scripts look for `./adb`, then the Android SDK platform-tools, then `PATH`. Set `ADB=/path/to/adb` to override, and `ANDROID_SERIAL` when more than one device is connected.

## Quick start

```bash
./diagnose.sh               # one-off read-only snapshot
./watch.sh --seconds 120    # timestamped trace while you plug, unplug or play
```

Start with a baseline: nothing recording and the cable left as it is. Then change one condition at a time and mark it from a second terminal:

```bash
./scripts/mark.sh synth_on
```

Each run writes its own directory under `logs/` (not tracked by git).

## Probe app

`test-app/` is a minimal Android app, **XZ1 Audio Probe**, that lists every input device Android exposes and records from the one you choose. It checks that the routed device is the one you asked for and stops if it is not.

```bash
./scripts/install-test-app.sh        # needs artifacts/xz1-audio-debug.apk, see docs/BUILD.md
./scripts/pull-recordings.sh
python3 scripts/analyze_wav.py logs/<recordings>/files/capture-<time>.wav
```

Defaults: 5 s, 48 kHz, mono, PCM16, source UNPROCESSED, strict routing.

## Files

| Path | Purpose |
|---|---|
| `diagnose.sh` | Read-only root snapshot: input devices, switch states, audio policy XML, AudioService/AudioPolicy dumps |
| `watch.sh` | Parallel timestamped capture of `getevent`, logcat, AudioService, AudioPolicy, sysfs and dmesg |
| `scripts/mark.sh` | Writes an experiment marker into the current trace |
| `scripts/mixer-snapshot.sh` | Full mixer and policy snapshot for a named state |
| `scripts/pcm-capture.sh` | Records one explicit PCM device for 5 s without touching the mixer |
| `scripts/analyze_wav.py` | Duration, RMS/dBFS, DC offset, peak and clipping of a WAV |
| `scripts/binaural-mixer.sh` | Stereo capture route and monitoring: `apply`, `restore`, `monitor-on`, `monitor-off` |
| `scripts/level-test.sh`, `scripts/raw_metrics.py` | Level and noise at several ADC gains |
| `scripts/howl-sweep.sh` | Finds where monitoring starts to feed back |
| `scripts/jack-compare-snap.sh` | Mixer, jack and policy snapshot for comparing plug states |
| `native/jackguard/` | Filters the 5-pole switch event that crashes Android 16 |
| `native/vcap/` | `vcap` (capture) and `vmix` (mixer write) through the phone's own `libtinyalsa.so` |
| `test-app/` | Probe app source and build script |
| `native/tinyalsa-2.0.0/` | TinyALSA 2.0.0 source (BSD-3-Clause), with a local `tinycap` fix |
| `tests/test_host.py` | Host-side tests with mocked ADB data |

See [docs/BUILD.md](docs/BUILD.md) to build the app and the native tools, and [docs/RUNBOOK.md](docs/RUNBOOK.md) for the full procedure.

## Binaries

Prebuilt binaries (the Probe APK and the arm64 tools) are attached to the [GitHub release](../../releases) of each `software-v*` tag. To use them, put them in `artifacts/` as described in [docs/BUILD.md](docs/BUILD.md).
