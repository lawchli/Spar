#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "$0")" && pwd)/scripts/common.sh"
device
root_check
new_logdir snapshot
capture() {
  local name="$1" command="$2" rc=0
  printf '%s\t%s\n' "$name" "$command" >> "$OUT/commands.tsv"
  python3 "$ROOT/scripts/bounded.py" 40 "$ADB" -s "$ANDROID_SERIAL" shell su -c "\"$command\"" > "$OUT/$name.txt" 2> "$OUT/$name.stderr" || rc=$?
  printf '%s\t%s\n' "$name" "$rc" >> "$OUT/status.tsv"
}
capture getprop 'getprop'
capture kernel 'uname -a; cat /proc/version; cat /proc/cmdline'
capture asound 'cat /proc/asound/cards; cat /proc/asound/pcm; cat /proc/asound/devices'
capture sound-nodes 'ls -la /sys/class/sound; ls -la /dev/snd; cat /proc/asound/card0/codec*'
capture audio 'dumpsys audio'
capture audio-policy 'dumpsys media.audio_policy'
capture audio-flinger 'dumpsys media.audio_flinger'
capture input 'getevent -lp; cat /proc/bus/input/devices'
capture input-state 'getevent -S'
capture switches 'ls -la /sys/class/switch; ls -la /sys/class/extcon'
capture processes 'ps -A; dumpsys media.metrics'
capture kernel-log 'dmesg'
capture logcat 'logcat -b all -d -v epoch'
capture tools 'command -v tinymix; command -v tinycap; command -v tinypcminfo; getenforce'
python3 "$ROOT/scripts/bounded.py" 40 "$ADB" -s "$ANDROID_SERIAL" shell su -c sh < "$ROOT/scripts/sysfs-state.sh" > "$OUT/sysfs-state.txt" 2> "$OUT/sysfs-state.stderr" || true
# Collect XML files without modifying any phone files. Includes ancillary policy includes.
adb_cmd shell su -c '"find -L /vendor/etc /system/etc /odm/etc /product/etc /system_ext/etc -type f -name \*.xml 2>/dev/null"' > "$OUT/xml-paths.txt" || true
python3 "$ROOT/scripts/collect_xml.py" "$OUT"
python3 "$ROOT/scripts/summarize.py" "$OUT"
echo "Snapshot complete: $OUT (status.tsv records failures; raw data retained)."
