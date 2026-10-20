#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
device
label="${1:-observation}"
[[ "$label" =~ ^[a-zA-Z0-9_-]+$ ]] || { echo 'Use an ASCII label: synth_on, tap_phone, unplug.' >&2; exit 2; }
adb_cmd shell log -p i -t XZ1MARK "$label"
date -u '+%Y-%m-%dT%H:%M:%SZ'
adb_cmd shell cat /proc/uptime
