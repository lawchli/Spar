#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
device
adb_cmd install -r "$ROOT/artifacts/xz1-audio-debug.apk"
adb_cmd shell pm grant org.xz1.audio android.permission.RECORD_AUDIO
adb_cmd shell am start -n org.xz1.audio/.MainActivity
echo 'Opened for enumeration only. Recording requires Start or explicit --ez auto true intent.'
