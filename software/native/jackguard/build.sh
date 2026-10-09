#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
: "${ANDROID_NDK_HOME:?Set ANDROID_NDK_HOME to an unpacked Android NDK}"
case "$(uname -s)" in Darwin) host=darwin-x86_64 ;; Linux) host=linux-x86_64 ;; *) echo 'Mac/Linux required' >&2; exit 2;; esac
CC="$ANDROID_NDK_HOME/toolchains/llvm/prebuilt/$host/bin/aarch64-linux-android28-clang"
OUT="$ROOT/artifacts/arm64-v8a"
mkdir -p "$OUT"
"$CC" -O2 -Wall -Wextra -fPIE -pie "$ROOT/native/jackguard/jackguard.c" -o "$OUT/jackguard"
shasum -a 256 "$OUT/jackguard"
