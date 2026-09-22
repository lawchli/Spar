#!/system/bin/sh
# Read only the documented state/name nodes; never traverse arbitrary sysfs attributes.
date -u '+wall=%Y-%m-%dT%H:%M:%SZ'
cat /proc/uptime
for base in /sys/class/switch/* /sys/class/extcon/*; do
  [ -e "$base" ] || continue
  for f in "$base/name" "$base/state" "$base"/cable.*/name "$base"/cable.*/state; do
    [ -r "$f" ] || continue
    echo "--- $f"; cat "$f"
  done
done
for base in /sys/class/input/event*/device; do
  [ -d "$base" ] || continue
  echo "--- $base"
  for attr in name phys capabilities/sw capabilities/key; do
    [ -r "$base/$attr" ] && { echo "$attr"; cat "$base/$attr"; }
  done
done
# EVIOCGSW via getevent -S supplies current SW bits even on kernels without h2w/extcon.
getevent -S 2>&1
