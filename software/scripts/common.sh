#!/usr/bin/env bash
# Sourced by scripts. Compatible with macOS Bash 3.2.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export ROOT
find_adb() {
  if [ -n "${ADB:-}" ]; then
    [ -x "$ADB" ] || ADB="$(command -v "$ADB")"
  else
    for candidate in "$ROOT/adb" "$PWD/adb" "$HOME/Library/Android/sdk/platform-tools/adb" "$HOME/Android/Sdk/platform-tools/adb" "${ANDROID_HOME:-/nonexistent}/platform-tools/adb"; do
      if [ -x "$candidate" ]; then ADB="$candidate"; break; fi
    done
    ADB="${ADB:-$(command -v adb || true)}"
  fi
  [ -n "$ADB" ] || { echo 'ADB not found. macOS: brew install --cask android-platform-tools; or set ADB=/path/to/adb' >&2; exit 2; }
}
device() {
  find_adb
  if [ -z "${ANDROID_SERIAL:-}" ]; then
    local found
    found="$("$ADB" devices | awk 'NR>1 && $2=="device" {print $1}')"
    [ "$(printf '%s\n' "$found" | awk 'NF {n++} END {print n+0}')" -eq 1 ] || {
      "$ADB" devices -l >&2
      echo 'Need exactly one authorized device, or set ANDROID_SERIAL.' >&2; exit 2;
    }
    ANDROID_SERIAL="$found"
  fi
  export ADB ANDROID_SERIAL
  "$ADB" -s "$ANDROID_SERIAL" get-state >/dev/null
}
adb_cmd() { "$ADB" -s "$ANDROID_SERIAL" "$@"; }
root_check() {
  # Allow the first Magisk authorization up to 30 seconds; no adb root/restart.
  local result
  result="$(python3 "$ROOT/scripts/bounded.py" 30 "$ADB" -s "$ANDROID_SERIAL" shell su -c id 2>&1)" || {
    printf '%s\n' "$result" >&2; echo 'Root unavailable; authorize ADB shell in Magisk then retry.' >&2; exit 2;
  }
  case "$result" in *uid=0*) ;; *) echo "Root unavailable: $result" >&2; exit 2;; esac
}
new_logdir() {
  umask 077
  local logroot="${XZ1_LOG_ROOT:-$ROOT/logs}"
  mkdir -p "$logroot"
  OUT="$(mktemp -d "$logroot/$(date -u +%Y%m%dT%H%M%SZ)-$1-XXXXXX")"
  export OUT
  printf '%s\n' "$OUT"
}
