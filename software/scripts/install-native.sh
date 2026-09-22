#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
device
root_check
abi="$(adb_cmd shell getprop ro.product.cpu.abi | tr -d '\r')"
[ "$abi" = arm64-v8a ] || { echo "Expected arm64-v8a; got $abi. Rebuild for this ABI first." >&2; exit 2; }
adb_cmd shell mkdir -p /data/local/tmp/xz1audio
for bin in tinymix tinypcminfo tinycap; do
  adb_cmd push "$ROOT/artifacts/arm64-v8a/$bin" "/data/local/tmp/xz1audio/$bin"
  adb_cmd shell chmod 755 "/data/local/tmp/xz1audio/$bin"
done
adb_cmd shell su -c '"/data/local/tmp/xz1audio/tinymix --version"'
echo 'Only /data/local/tmp/xz1audio tools installed; no mixer values changed.'
