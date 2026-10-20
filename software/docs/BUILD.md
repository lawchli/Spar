# Build

Build outputs go to `artifacts/`, which git ignores. Prebuilt copies are attached to each `software-v*` release; download them into the same layout instead of building if you prefer:

```text
artifacts/xz1-audio-debug.apk
artifacts/arm64-v8a/tinymix
artifacts/arm64-v8a/tinypcminfo
artifacts/arm64-v8a/tinycap
artifacts/arm64-v8a/vcap
artifacts/arm64-v8a/vmix
artifacts/arm64-v8a/jackguard
```

## Probe app

Requires JDK 17+, Android SDK platform 35 and build-tools 35.0.0. No Gradle.

```bash
export ANDROID_SDK_ROOT="$HOME/Library/Android/sdk"
export ANDROID_BUILD_TOOLS="$ANDROID_SDK_ROOT/build-tools/35.0.0"
./test-app/build.sh
```

The script creates a local debug keystore (not committed). A self-built APK is signed differently from the released one; if installing over it fails, pull your recordings first, then uninstall `org.xz1.audio` (this deletes the app's recordings).

The app runs on API 28+ and targets API 35. It records 48 kHz mono 16-bit PCM and has no network, broad storage or background-recording permissions.

## Native tools

Requires the official Android NDK r27c.

```bash
export ANDROID_NDK_HOME="$HOME/Library/Android/sdk/ndk/27.2.12479018"
./native/build.sh              # tinymix, tinypcminfo, tinycap, vcap, vmix
./native/jackguard/build.sh    # jackguard
```

The output is arm64-v8a for Android API 28+. `vcap` and `vmix` load the phone's own `libtinyalsa.so` at run time. TinyALSA 2.0.0 is upstream source except for a local fix in `utils/tinycap.c`; see [native/PROVENANCE.md](../native/PROVENANCE.md) and the license in `native/tinyalsa-2.0.0/NOTICE`.

## Host tests

The tests use mocked ADB data only; they check the WAV maths, error handling, XML collection and the watcher lifecycle, not a real phone.

```bash
python3 tests/test_host.py
python3 -m compileall -q scripts tests
for f in diagnose.sh watch.sh scripts/*.sh test-app/build.sh native/build.sh; do bash -n "$f"; done
```

## Undo

- Stopping the watcher only ends the ADB child processes it started; it does not kill the ADB server.
- The diagnostic tools never remount, flash or write to sysfs, SELinux or the mixer.
- `binaural-mixer.sh restore` (or a reboot) returns the mixer to its idle values; stopping `jackguard` releases the headset input device.
- To remove the app: `adb uninstall org.xz1.audio` (pull recordings first).
- Native tools are installed only in `/data/local/tmp/xz1audio/`; that directory can be deleted once recordings are pulled.
