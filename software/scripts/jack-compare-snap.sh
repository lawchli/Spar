#!/usr/bin/env bash
# Snapshot playback-side state for comparing jack insertion types.
# Usage: ADB_SERVER_PORT=5038 ANDROID_SERIAL=<serial> scripts/jack-compare-snap.sh <label>
set -euo pipefail
label="${1:?label}"
out="logs/$(date -u +%Y%m%dT%H%M%SZ)-jackcmp-$label"
mkdir -p "$out"
a() { adb -s "$ANDROID_SERIAL" "$@"; }
a shell su -c '"/data/local/tmp/xz1audio/tinymix -D 0 contents"' > "$out/tinymix.txt" 2>&1
a shell su -c '"dmesg | tail -n 300"' > "$out/dmesg-tail.txt" 2>&1
a shell su -c '"getevent -lp 2>/dev/null | grep -A12 -i jack; cat /proc/asound/card0/jack* 2>/dev/null"' > "$out/jack.txt" 2>&1 || true
a shell dumpsys media.audio_policy > "$out/audio-policy.txt" 2>&1
a shell dumpsys media.audio_flinger > "$out/audio-flinger.txt" 2>&1
a shell su -c '"tail -20 /data/local/tmp/jackguard.log"' > "$out/jackguard.txt" 2>&1
echo "$out"
