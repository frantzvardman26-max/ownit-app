#!/bin/bash
BT=/usr/local/lib/android/sdk/build-tools/$(ls /usr/local/lib/android/sdk/build-tools | sort -V | tail -1)
for f in apks/*.apk;
do echo "=================== $f";
pkg=$($BT/aapt2 dump packagename "$f" 2>/dev/null);
adb uninstall "$pkg" >/dev/null 2>&1;
adb install -r -g "$f" | tail -1;
adb logcat -c;
adb shell monkey -p "$pkg" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1;
sleep 12;
if adb shell pidof "$pkg" >/dev/null;
then echo "RESULT $pkg: running OK";
else echo "RESULT $pkg: NOT RUNNING";
fi;
adb logcat -d -b crash | head -60;
adb logcat -d | grep -E "FATAL EXCEPTION|AndroidRuntime" -A25 | head -50;
done
