#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/scripts/common.sh"
device
root_check
new_logdir watch
python3 "$ROOT/scripts/watcher.py" --out "$OUT" "$@"
