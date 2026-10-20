#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
label="${1:-idle}"
case "$label" in idle|builtin_recording|wired_detected|wired_requested) ;; *) echo 'Label: idle | builtin_recording | wired_detected | wired_requested' >&2; exit 2;; esac
device
root_check
new_logdir "mixer-$label"
python3 "$ROOT/scripts/bounded.py" 30 "$ADB" -s "$ANDROID_SERIAL" shell su -c '"/data/local/tmp/xz1audio/tinymix -D 0 contents"' > "$OUT/tinymix.txt" 2> "$OUT/tinymix.stderr"
adb_cmd shell dumpsys media.audio_policy > "$OUT/audio-policy.txt"
adb_cmd shell dumpsys media.audio_flinger > "$OUT/audio-flinger.txt"
adb_cmd shell su -c '"cat /proc/asound/pcm; cat /proc/uptime; date -u"' > "$OUT/pcm-clock.txt"
echo "$label is your experimental label, not proof of physical detection; verify policy and getevent."
echo "Compare: diff -u logs/<earlier>/tinymix.txt '$OUT/tinymix.txt'"
