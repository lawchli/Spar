#!/usr/bin/env bash
# Root-only: find where the sidetone monitor starts to self-oscillate.
#
#   scripts/howl-sweep.sh <label> [from] [to] [step]     (default 70 100 2)
#
# Steps IIR0/IIR1 INP0 Volume (written value, 84 = 0 dB, 1 dB per step) while
# capturing the binaural input with vcap. Between captures the IIR volume drops
# to 54 (-30 dB) so a howl never lasts more than one capture. Stops at the first
# step whose strongest 2-5 kHz tone stands >= HOWL_DB (default 15) above the
# band median; afterwards the IIR volume goes back to its value before the run.
#
# Needs `binaural-mixer.sh apply` and `monitor-on` first. Source connected but
# silent, headphones plugged in (they are part of the feedback path) but NOT
# worn: an oscillation at full HPH gain is loud. RX=<n> also sets RX1/RX2
# Digital Volume (84 = 0 dB) for the run; ADC gain is left as it is.
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
label="${1:?usage: howl-sweep.sh <label> [from] [to] [step]}"
from="${2:-70}"; to="${3:-100}"; step="${4:-2}"
secs="${SECS:-2}"; howl_db="${HOWL_DB:-15}"
case "$label" in *[!A-Za-z0-9._-]*) echo 'label: letters, digits, . _ - only' >&2; exit 2;; esac
device
root_check
D=/data/local/tmp/xz1audio
T="$D/tinymix -D 0"
get() { adb_cmd shell su -c "\"$T get $1\"" | cut -d' ' -f1 | tr -d '\r'; }

adb_cmd shell su -c "\"$T get 207\"" | grep -q '> SRC0' ||
  { echo 'Monitor is off (RX INT1 MIX2 INP is not SRC0); run binaural-mixer.sh monitor-on first.' >&2; exit 2; }
# Digital volumes below 84 (0 dB) read back as written + 256.
old_iir="$(get 64)"; old_iir=$((old_iir > 168 ? old_iir - 256 : old_iir))
[ -z "${RX:-}" ] || adb_cmd shell su -c "\"$T set 38 $RX; $T set 39 $RX\""
new_logdir "howl-$label" >/dev/null
{
  echo "ADC2/3: $(get 32) / $(get 33)"
  echo "RX1/2 Digital Volume (read back): $(get 38) / $(get 39)"
  echo "HPHL/R Volume: $(get 25) / $(get 26)"
  echo "IIR INP0 Volume before run (written value): $old_iir"
} | tee "$OUT/settings.txt"
echo "$OUT"

trap 'adb_cmd shell su -c "\"$T set 64 $old_iir; $T set 68 $old_iir\""' EXIT
v="$from"
while [ "$v" -le "$to" ]; do
  adb_cmd shell su -c "\"cd $D; $T set 64 $v; $T set 68 $v; sleep 0.3;
    timeout $((secs + 10)) ./vcap hs_$v.raw 0 0 2 48000 960 4 $secs >/dev/null || echo vcap failed;
    $T set 64 54; $T set 68 54; chmod 644 hs_$v.raw\""
  adb_cmd pull "$D/hs_$v.raw" "$OUT/iir$v.raw" >/dev/null 2>&1
  adb_cmd shell su -c "\"rm -f $D/hs_$v.raw\""
  line="$(cd "$OUT" && python3 "$ROOT/scripts/raw_metrics.py" --lo 2000 --hi 5000 --skip 0.3 "iir$v.raw")"
  echo "IIR $v ($((v - 84)) dB)  $line" | tee -a "$OUT/metrics.txt"
  prom="$(printf '%s\n' "$line" | grep -o '(+[0-9.-]*)' | tr -d '(+)' | sort -n | tail -1)"
  if awk -v p="$prom" -v t="$howl_db" 'BEGIN {exit !(p >= t)}'; then
    echo "Oscillation at IIR $v ($((v - 84)) dB): tone prominence $prom dB >= $howl_db. Stopping." | tee -a "$OUT/metrics.txt"
    break
  fi
  v=$((v + step))
done
