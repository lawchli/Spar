#!/usr/bin/env bash
# Root-only: capture the binaural input at several ADC gains with vcap and
# report level, peak and the strongest 1-6 kHz tone per channel. Used to compare
# series-resistor values: run once with the source silent (noise) and once at
# full level (signal), same label prefix.
#
#   scripts/level-test.sh <label> [ADC gains...]     (default gains: 11 14 17 20)
#   SECS=5 scripts/level-test.sh r10k-sig 14 17 20
#
# Needs `binaural-mixer.sh apply` first. Restores ADC2/ADC3 to the value they
# had before. Jack and headset-button input events during the run are logged:
# a button event means the signal swing on the mic line reached the MBHC button
# window, i.e. the series resistor is too small for that source level.
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
label="${1:?usage: level-test.sh <label> [ADC gains...]}"; shift
gains="${*:-11 14 17 20}"
secs="${SECS:-5}"
case "$label" in *[!A-Za-z0-9._-]*) echo 'label: letters, digits, . _ - only' >&2; exit 2;; esac
device
root_check
new_logdir "level-$label" >/dev/null
D=/data/local/tmp/xz1audio
n=0; for _ in $gains; do n=$((n+1)); done
total=$(( n * (secs + 2) + 5 ))

adb_cmd shell su -c "\"
cd $D; T=./tinymix
old=\\\$(\\\$T -D 0 get 33 | cut -d' ' -f1)
timeout $total getevent -lt /dev/input/event9 > lt_jack.txt 2>&1 &
timeout $total getevent -lt /dev/input/event10 > lt_button.txt 2>&1 &
sleep 1
for g in $gains; do
  \\\$T -D 0 set 33 \\\$g; \\\$T -D 0 set 32 \\\$g
  timeout $((secs + 10)) ./vcap lt_${label}_\\\$g.raw 0 0 2 48000 960 4 $secs >/dev/null || echo vcap failed at \\\$g
  chmod 644 lt_${label}_\\\$g.raw
done
\\\$T -D 0 set 33 \\\$old; \\\$T -D 0 set 32 \\\$old
wait
chmod 644 lt_jack.txt lt_button.txt
\""
for g in $gains; do
  adb_cmd pull "$D/lt_${label}_$g.raw" "$OUT/adc$g.raw" >/dev/null 2>&1
done
adb_cmd pull "$D/lt_jack.txt" "$OUT/events-jack.txt" >/dev/null 2>&1
adb_cmd pull "$D/lt_button.txt" "$OUT/events-button.txt" >/dev/null 2>&1
adb_cmd shell su -c "\"rm -f $D/lt_${label}_*.raw $D/lt_jack.txt $D/lt_button.txt\""
adb_cmd shell su -c "\"tail -20 /data/local/tmp/jackguard.log\"" > "$OUT/jackguard-tail.txt"

echo "$OUT"
(cd "$OUT" && for g in $gains; do python3 "$ROOT/scripts/raw_metrics.py" "adc$g.raw"; done) | tee "$OUT/metrics.txt"
for f in jack button; do
  events="$(grep -c 'EV_KEY\|EV_SW' "$OUT/events-$f.txt" || true)"
  echo "$f input events during run: $events"
  [ "$events" = 0 ] || grep 'EV_KEY\|EV_SW' "$OUT/events-$f.txt" | head -10
done
