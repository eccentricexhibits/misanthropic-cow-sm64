# In-game screenshot test

Runs sm64coopdx on a virtual display with the mod and a test mod that hides the HUD and
holds her in a series of poses, and saves a screenshot of each. Screenshots stay on your
machine; they show the game and shouldn't be committed.

```bash
# Linux packages: xvfb imagemagick, plus sm64coopdx's own build dependencies
cp -r ../../mod/misanthropic-cow zz-cow-screenshot-test <sm64coopdx>/build/us_pc/mods/
./run_screenshots.sh <sm64coopdx>/build/us_pc <output folder> <your ROM>
```

Only on a machine without IPv6 (some containers): sm64coopdx hosts on an IPv6 socket, so
build the shim and pass it in:

```bash
gcc -shared -fPIC -O2 -o ipv6to4.so ipv6to4.c -ldl
SHIM=$PWD/ipv6to4.so ./run_screenshots.sh <sm64coopdx>/build/us_pc <output folder> <your ROM>
```
