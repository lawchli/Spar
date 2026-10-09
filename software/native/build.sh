#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to an unpacked Android NDK (r27c built the committed binaries; r30 on the Mac)}"
case "$(uname -s)" in Darwin) host=darwin-x86_64 ;; Linux) host=linux-x86_64 ;; *) echo 'Mac/Linux required' >&2; exit 2;; esac
CC="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/$host/bin/aarch64-linux-android28-clang"
SRC="$ROOT/native/tinyalsa-2.0.0"
OUT="$ROOT/artifacts/arm64-v8a"
mkdir -p "$OUT"
for name in tinymix tinypcminfo tinycap; do
  "$CC" -O2 -fPIE -pie -I"$SRC/include" -I"$SRC/src" "$SRC/utils/$name.c" "$SRC"/src/*.c -ldl -o "$OUT/$name"
done
# vcap / vmix load the phone's own libtinyalsa.so at run time (see native/vcap/).
for name in vcap vmix; do
  "$CC" -O2 -fPIE -pie "$ROOT/native/vcap/$name.c" -ldl -o "$OUT/$name"
done
python3 - "$OUT" <<'PY'
import hashlib,sys
from pathlib import Path
p=Path(sys.argv[1])
(p/'SHA256SUMS').write_text(''.join(hashlib.sha256((p/n).read_bytes()).hexdigest()+'  '+n+'\n' for n in ['tinymix','tinypcminfo','tinycap','vcap','vmix']))
PY
echo "Built arm64 Android API 28+ tools: $OUT"
