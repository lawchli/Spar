#!/usr/bin/env bash
# Root-only, temporary: route the 5-pole extra mic (ADC3) and the headset mic
# (ADC2) to a two-channel SLIM_0_TX capture on MultiMedia1 (PCM 0), following
# vendor mixer_paths_tasha.xml "binaural-mic" without the monitoring sub-path.
#
#   scripts/binaural-mixer.sh show | apply | restore | monitor-on | monitor-off
#
# monitor-on adds vendor "binaural-mic-monitoring": codec sidetone IIR0/IIR1
# from DEC7/DEC8 into RX INT1/INT2 (HPHL/HPHR), no Android path involved.
#
# Restore values are an idle mixer snapshot of the test phone
# (G8441, LineageOS 23.2-20260919, 2026-10-05). Control IDs are checked against
# names before every write; a mismatch aborts without writing.
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/common.sh"
TM=/data/local/tmp/xz1audio/tinymix
VMIX=/data/local/tmp/xz1audio/vmix

# id|name|apply value|restore value
# 3131 is what the HAL sets for its own headset-mic capture (app type 69938,
# ACDB device 147, 48 kHz, backend 3). Without it the ADSP refuses to start
# AFE port 0x4001 (SLIMBUS_0_TX), "backend prepare failed -131".
CONTROLS='277|AIF1_CAP Mixer SLIM TX7|1|0
278|AIF1_CAP Mixer SLIM TX8|1|0
219|SLIM TX7 MUX|DEC7|ZERO
220|SLIM TX8 MUX|DEC8|ZERO
234|ADC MUX7|AMIC|AMIC
235|ADC MUX8|AMIC|AMIC
260|AMIC MUX7|ADC3|ZERO
261|AMIC MUX8|ADC2|ZERO
82|TX7 HPF cut off|CF_NEG_3DB_4HZ|CF_NEG_3DB_4HZ
83|TX8 HPF cut off|CF_NEG_3DB_4HZ|CF_NEG_3DB_4HZ
62|DEC7 Volume|84|84
63|DEC8 Volume|84|84
33|ADC3 Volume|12|0
32|ADC2 Volume|12|12
4220|SLIM_0_TX Channels|Two|One
4233|SLIM_0_TX Format|S24_LE|S16_LE
1433|MultiMedia1 Mixer SLIM_0_TX|1|0
3131|Audio Stream Capture 0 App Type Cfg|69938 147 48000 3|0 0 0 0'

# Digital volumes read back as the raw signed register + 84 (write 80 reads
# 336, write 54 reads 310 = the idle snapshot), so restore writes 54.
# IIR band coefficients: 268435456 (1.0 in Q28) in b0 is pass-through, the
# boot default. Something zeroed them on 2026-10-09, muting the sidetone
# completely, so monitor-on writes them explicitly.
MONITOR='207|RX INT1 MIX2 INP|SRC0|ZERO
112|IIR0 Band1|268435456 0 0 0 0|268435456 0 0 0 0
113|IIR0 Band2|268435456 0 0 0 0|268435456 0 0 0 0
114|IIR0 Band3|268435456 0 0 0 0|268435456 0 0 0 0
115|IIR0 Band4|268435456 0 0 0 0|268435456 0 0 0 0
116|IIR0 Band5|268435456 0 0 0 0|268435456 0 0 0 0
117|IIR1 Band1|268435456 0 0 0 0|268435456 0 0 0 0
118|IIR1 Band2|268435456 0 0 0 0|268435456 0 0 0 0
119|IIR1 Band3|268435456 0 0 0 0|268435456 0 0 0 0
120|IIR1 Band4|268435456 0 0 0 0|268435456 0 0 0 0
121|IIR1 Band5|268435456 0 0 0 0|268435456 0 0 0 0
208|RX INT2 MIX2 INP|SRC1|ZERO
313|IIR0 INP0 MUX|DEC7|ZERO
317|IIR1 INP0 MUX|DEC8|ZERO
64|IIR0 INP0 Volume|80|54
68|IIR1 INP0 Volume|80|54
102|IIR0 Enable Band1|1|0
103|IIR0 Enable Band2|1|0
104|IIR0 Enable Band3|1|0
105|IIR0 Enable Band4|1|0
106|IIR0 Enable Band5|1|0
107|IIR1 Enable Band1|1|0
108|IIR1 Enable Band2|1|0
109|IIR1 Enable Band3|1|0
110|IIR1 Enable Band4|1|0
111|IIR1 Enable Band5|1|0
336|RX INT1 DEM MUX|CLSH_DSM_OUT|CLSH_DSM_OUT
337|RX INT2 DEM MUX|CLSH_DSM_OUT|CLSH_DSM_OUT
25|HPHL Volume|20|20
26|HPHR Volume|20|20
38|RX1 Digital Volume|75|84
39|RX2 Digital Volume|75|84'

mode="${1:-show}"
case "$mode" in
  show|apply|restore) ;;
  monitor-on) mode=apply; CONTROLS="$MONITOR" ;;
  monitor-off) mode=restore; CONTROLS="$MONITOR" ;;
  *) echo 'Usage: binaural-mixer.sh show|apply|restore|monitor-on|monitor-off' >&2; exit 2;;
esac
device
root_check

# Verify every id still carries the expected name before touching anything.
names="$(adb_cmd shell su -c "\"$TM -D 0 contents\"" | awk -F'\t' 'NR>2 {print $1"\t"$4}')"
while IFS='|' read -r id name _ _; do
  line="$(printf '%s\n' "$names" | awk -F'\t' -v id="$id" '$1==id {print $2}')"
  case "$line" in "$name"|"$name "*) ;; *) echo "Control $id is not '$name' (got '$line'); aborting." >&2; exit 2;; esac
done <<< "$CONTROLS"

script=''
while IFS='|' read -r id name on off; do
  # TinyALSA 2.0 tinymix rejects the Q28 IIR coefficients (declared range
  # 0..255) yet exits 0; vmix writes them through the phone's libtinyalsa.
  set_cmd="$TM -D 0 set"
  case "$name" in IIR?" Band"?) set_cmd="$VMIX 0" ;; esac
  case "$mode" in
    apply) script="$script$set_cmd $id $on >/dev/null || echo 'FAILED $id $name';" ;;
    restore) script="$script$set_cmd $id $off >/dev/null || echo 'FAILED $id $name';" ;;
  esac
  script="$script$TM -D 0 get $id | cut -c1-120 | sed 's/^/$id $name: /';"
done <<< "$CONTROLS"
adb_cmd shell su -c "\"$script\""
