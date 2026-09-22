#!/usr/bin/env bash
# Build without Gradle: official Android SDK build-tools + JDK 17+.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SDK="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-$HOME/Library/Android/sdk}}"
ANDROID_JAR="${ANDROID_JAR:-$SDK/platforms/android-35/android.jar}"
BT="${ANDROID_BUILD_TOOLS:-$SDK/build-tools/35.0.0}"
AAPT="${AAPT:-$BT/aapt}"
D8="${D8:-$BT/d8}"
APKSIGNER="${APKSIGNER:-$BT/apksigner}"
ZIPALIGN="${ZIPALIGN:-$BT/zipalign}"
B="$ROOT/test-app/build"
mkdir -p "$B/classes" "$B/dex" "$ROOT/artifacts"
find "$ROOT/test-app/src" -name '*.java' > "$B/sources.txt"
javac -encoding UTF-8 -source 8 -target 8 -classpath "$ANDROID_JAR" -d "$B/classes" @"$B/sources.txt"
jar cf "$B/classes.jar" -C "$B/classes" .
"$D8" --min-api 28 --lib "$ANDROID_JAR" --output "$B/dex" "$B/classes.jar"
"$AAPT" package -f -M "$ROOT/test-app/AndroidManifest.xml" -I "$ANDROID_JAR" -F "$B/unsigned.apk"
(cd "$B/dex" && zip -q -u "$B/unsigned.apk" classes.dex)
if [ -x "$ZIPALIGN" ]; then "$ZIPALIGN" -f 4 "$B/unsigned.apk" "$B/aligned.apk"; else cp "$B/unsigned.apk" "$B/aligned.apk"; fi
KEY="${XZ1_DEBUG_KEYSTORE:-$B/debug.keystore}"
if [ ! -f "$KEY" ]; then
  keytool -genkeypair -keystore "$KEY" -storepass android -keypass android -alias xz1debug -keyalg RSA -keysize 2048 -validity 3650 -dname 'CN=XZ1 Audio Debug'
fi
"$APKSIGNER" sign --ks "$KEY" --ks-pass pass:android --key-pass pass:android --ks-key-alias xz1debug --out "$ROOT/artifacts/xz1-audio-debug.apk" "$B/aligned.apk"
"$APKSIGNER" verify --verbose --print-certs "$ROOT/artifacts/xz1-audio-debug.apk"
python3 - "$ROOT/artifacts/xz1-audio-debug.apk" <<'PY'
import hashlib,sys
from pathlib import Path
p=Path(sys.argv[1]); (p.parent/'SHA256SUMS').write_text(hashlib.sha256(p.read_bytes()).hexdigest()+'  '+p.name+'\n')
PY
