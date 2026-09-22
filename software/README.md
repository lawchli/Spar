# Spar software

Phone-side tools for Spar, run from a Mac or Linux host over ADB.

This version (v0.1) is the diagnostic kit used to find out how the phone detects a wired headset and where its microphone input is routed. It collects evidence only: it does not modify the system, the mixer or SELinux.

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
| `test-app/` | Probe app source and build script |
| `native/` | TinyALSA 2.0.0 source (BSD-3-Clause) and the NDK build script |
| `tests/test_host.py` | Host-side tests with mocked ADB data |

See [docs/BUILD.md](docs/BUILD.md) to build the app and the native tools, and [docs/RUNBOOK.md](docs/RUNBOOK.md) for the full procedure.

## Binaries

Prebuilt binaries (the probe APK and arm64 `tinymix`, `tinypcminfo` and `tinycap`) are attached to the [GitHub release](../../releases) of each `software-v*` tag. To use them, put them in `artifacts/` as described in [docs/BUILD.md](docs/BUILD.md).
