#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
device
new_logdir recordings
adb_cmd pull /sdcard/Android/data/org.xz1.audio/files "$OUT/"
echo "WAV and JSONL route evidence: $OUT/files"
