# Runbook

How to use the kit to find out whether the phone detects an input on the headphone jack and where it routes it. Change one condition at a time and keep every run's output directory.

## 1. Baseline without recording

Close any recording app and leave the cable as it is. Run `./diagnose.sh`, then `./watch.sh --seconds 120`. The first root request may need approval in Magisk.

In the snapshot, check `status.tsv` first: a non-zero exit code or stderr means the collection failed, not that the state is absent.

- `getevent -lp` maps each input device's switch and key capabilities to its `/dev/input/eventX`. The number depends on enumeration; do not hard-code it. A sound card may expose jack switches and buttons as separate input devices.
- `getevent -S` gives the initial switch bits and `getevent -lt` the later changes.
- Older kernels may have no `/sys/class/extcon`. If every sysfs state is missing, rely on the input switches and the framework trace.

Summarise a trace with:

```bash
python3 scripts/watch-excerpts.py logs/<watch-dir>
```

It aligns the device monotonic clock, `/proc/uptime`, host UTC and logcat time. Polled dumps can miss short states, so always read them together with the real-time events. AudioService repeats its connection history in every dump; do not count repeats as new events.

Events worth following: `SW_MICROPHONE_INSERT`, `SW_HEADPHONE_INSERT`, `SW_JACK_PHYSICAL_INSERT`, and `KEY_MEDIA`, `KEY_PLAYPAUSE`, `KEY_VOLUME*` and `KEY_VOICECOMMAND`.

## 2. One change per experiment

Start a new watcher for each experiment. From another terminal, mark what you do (`./scripts/mark.sh synth_on`, `synth_muted`, `tap_phone`), and do it right after the mark. Do not change level, cable, app and mixer in the same experiment.

## 3. Framework device and actual route

Install the probe app with `./scripts/install-test-app.sh`. With nothing recording, check whether the input list steadily contains a wired headset (type 3, `TYPE_WIRED_HEADSET`).

Then select it, source UNPROCESSED, 5 s. Strict mode is on by default:

- if `setPreferredDevice` is rejected, the app reports an error;
- if the routed device differs, recording stops;
- for up to 1.5 s after start the route may still be null, and that audio is discarded.

The app can also be started from the host:

```bash
adb shell am start -n org.xz1.audio/.MainActivity --ei device_id 123 --es source UNPROCESSED --ei seconds 30 --ez strict true --ez auto true
```

`123` is a placeholder; take the current ID from the app, as it changes on reconnect. Supported sources: MIC, UNPROCESSED, DEFAULT, CAMCORDER. The app tries to disable AEC/NS/AGC on its own session and logs the result; vendor processing may still apply.

If the list has no wired input at all, the problem is detection (MBHC or framework), not the recording app.

## 4. Is the audio really from the source?

Keep the route check and the watcher running, and record a window of source muted → tone → source muted. Compare it separately with tapping the phone. Start at a low level.

```bash
./scripts/pull-recordings.sh
python3 scripts/analyze_wav.py <file.wav>
python3 scripts/analyze_wav.py <file.wav> --start 2 --seconds 2
```

RMS alone does not prove the source; analog clipping can happen below digital full scale. A separate recording with the built-in mic is a useful control.

## 5. HAL and mixer, only when needed

```bash
./scripts/install-native.sh
./scripts/mixer-snapshot.sh idle
# run each in the matching real state; the script does not create or switch states
./scripts/mixer-snapshot.sh builtin_recording
./scripts/mixer-snapshot.sh wired_detected
./scripts/mixer-snapshot.sh wired_requested
diff -u logs/<idle>/tinymix.txt logs/<wired_requested>/tinymix.txt
```

Compare the Headset Mic, AMIC, ADC, TX, DEC and SLIMBUS controls, then trace them to the audio policy XML paths and the platform backend.

This kit never writes mixer values. If you later decide to change one, first save every control's old value and type, prepare and check a restore, and then change the smallest set. The HAL may overwrite the mixer at any time, so a manual change that works is not a persistent fix.

## 6. Capturing an explicit PCM

Choose at most one to three front-ends, using the HAL log, `/proc/asound/pcm` and the XML; front-end numbers are not fixed.

```bash
./scripts/pcm-capture.sh <capture-device-number>
```

Defaults are card 0, 48 kHz, mono, 16-bit, 5 s. It records `tinypcminfo`, the mixer before and after, the WAV, metrics and exit codes. Without an active route it records nothing. Some `tinycap` failures still exit 0, so check duration and frame count. A raw capture does not replace a framework recording as proof that the input works.
