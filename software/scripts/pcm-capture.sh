#!/usr/bin/env bash
# One explicitly selected capture PCM; never scans devices or writes mixer controls.
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
pcm="${1:-}"
[[ "$pcm" =~ ^[0-9]+$ ]] || { echo 'Usage: scripts/pcm-capture.sh PCM_DEVICE_ID [rate=48000] [channels=1] [bits=16]' >&2; exit 2; }
rate="${2:-48000}"; channels="${3:-1}"; bits="${4:-16}"
[[ "$rate" =~ ^[0-9]+$ && "$channels" =~ ^[12]$ && "$bits" =~ ^(16|24|32)$ ]] || { echo 'Invalid PCM parameters' >&2; exit 2; }
device
root_check
new_logdir "pcm-$pcm"
remote="/data/local/tmp/xz1audio/capture-$(date -u +%Y%m%dT%H%M%SZ)-$$.wav"
adb_cmd shell su -c '"/data/local/tmp/xz1audio/tinymix -D 0 contents"' > "$OUT/mixer-before.txt"
adb_cmd shell su -c '"/system/bin/timeout --help"' > "$OUT/timeout-help.txt" 2>&1 || true
python3 "$ROOT/scripts/bounded.py" 20 "$ADB" -s "$ANDROID_SERIAL" shell su -c "\"/data/local/tmp/xz1audio/tinypcminfo -D 0 -d $pcm\"" > "$OUT/pcminfo.txt" 2>&1
rc=0
# On-device SIGINT finalizes the WAV; KILL after 3s bounds a wedged capture.
python3 "$ROOT/scripts/bounded.py" 25 "$ADB" -s "$ANDROID_SERIAL" shell su -c "\"/system/bin/timeout -s INT -k 3 15 /data/local/tmp/xz1audio/tinycap $remote -D 0 -d $pcm -c $channels -r $rate -b $bits -t 5\"" > "$OUT/capture.txt" 2>&1 || rc=$?
printf '%s\n' "$rc" > "$OUT/exit-status.txt"
adb_cmd shell su -c "\"chmod 644 $remote\"" || true
adb_cmd pull "$remote" "$OUT/capture.wav" || true
adb_cmd shell su -c '"/data/local/tmp/xz1audio/tinymix -D 0 contents"' > "$OUT/mixer-after.txt"
if [ -f "$OUT/capture.wav" ]; then python3 "$ROOT/scripts/analyze_wav.py" "$OUT/capture.wav" > "$OUT/metrics.json"; fi
echo "Logs: $OUT. Exit=$rc. Inspect duration; tinycap can return 0 with zero frames on open failure."
exit "$rc"
