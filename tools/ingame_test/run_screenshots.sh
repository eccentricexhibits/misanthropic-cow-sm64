#!/bin/bash
# Run sm64coopdx under a virtual display and capture a screenshot whenever the test mod asks for one.
# Usage: run_screenshots.sh <game dir> <out dir> <your ROM>
GAME="$1"; OUT="$2"; ROM="$3"; mkdir -p "$OUT/save"; cp "$ROM" "$OUT/save/baserom.us.z64"
printf "enable-mod: misanthropic-cow\nenable-mod: zz-cow-screenshot-test\n" > "$OUT/save/sm64config.txt"
export DISPLAY=:99 SDL_AUDIODRIVER=dummy LIBGL_ALWAYS_SOFTWARE=1
Xvfb :99 -screen 0 960x720x24 >/dev/null 2>&1 & XPID=$!
sleep 2
cd "$GAME"
${SHIM:+LD_PRELOAD=$SHIM} stdbuf -oL -eL ./sm64coopdx --server 7777 --skip-intro --hide-loading-screen --skip-update-check --no-discord --windowed \
  --width 960 --height 720 --savepath "$OUT/save" --playername Tester \
  --enable-mod misanthropic-cow --enable-mod zz-cow-screenshot-test > "$OUT/game.log" 2>&1 & GPID=$!
for i in $(seq 1 900); do
  sleep 1
  while read -r line; do
    n=$(echo "$line" | awk '{print $2"_"$3}')
    [ -f "$OUT/shot_$n.png" ] || import -display :99 -window root "$OUT/shot_$n.png"
  done < <(grep -a "^SHOT " "$OUT/game.log" 2>/dev/null || true)
  grep -aq "SHOTS DONE" "$OUT/game.log" && break
  kill -0 $GPID 2>/dev/null || { echo "game exited"; break; }
  [ $((i % 60)) -eq 0 ] && import -display :99 -window root "$OUT/at_${i}s.png"
done
kill $GPID 2>/dev/null; sleep 1; kill $XPID 2>/dev/null
ls "$OUT"
