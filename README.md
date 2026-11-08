# The Misanthropic Cow for sm64coopdx

A mod that adds The Misanthropic Cow as a playable character in
[sm64coopdx](https://github.com/coop-deluxe/sm64coopdx), the PC version of Super Mario 64.
She uses her own animations where they fit (idle, walk, run, tiptoe, jump, fall,
land, skid, hurt, death, victory) and Mario's for every other action.

**This repo contains no game files.** To play, you need sm64coopdx installed with
your own copy of the game. Never add a ROM or anything extracted from one here.

![The game-ready model from the front, three-quarter, side and back](renders/turnaround_game.png)

## What's in this repo

| Path | What it is |
|---|---|
| `model/misanthropic_cow_game.glb` | The game-ready model: 19,970 triangles, with her rig, all 41 animations and baked textures |
| `model/misanthropic_cow_game.blend` | The same model as a Blender working file |
| `model/textures/` | The baked textures as PNGs (64–512 px) |
| `model/misanthropic_cow_sm64_rig.blend` | The model fitted to Mario's 20-joint skeleton, for previews |
| `model/misanthropic_cow_sm64_rig.json` | Her joint offsets, joint frames and scale for that rig |
| `renders/` | Preview renders |
| `tools/` | The conversion scripts |

The full-quality original model (1.4 million triangles, 105 MB) is not stored here.

## Status

| Step | State |
|---|---|
| Inspect the source model (1.4M triangles, 58 bones, 41 animations) | Done |
| Reduce to about 20k triangles and bake clean textures (64–512 px) | Done |
| Fit her to Mario's 20-joint skeleton with her own proportions, about 1.3× his height | Done |
| Convert her animations to the game's format | Next |
| Export the sm64coopdx mod (model + Lua) | To do |

## Her rig

![Her model posed by eight of Mario's animations](renders/poses_mario_animations.png)

She is fitted to the 20 animated joints the game uses for Mario, but with her own bone
lengths, so Mario's animations play on her proportions. Her height is set to about 1.3×
Mario's (about 200 game units against his 155), which is one setting in `build_rig.py`.
Mario's animations are scaled to her leg length, so her feet stay on the ground.
Her belly, udders, fur and tail are fixed to her torso and hips for now.

## Tools

The scripts in `tools/` run with Blender 5.1 as a Python module (`pip install bpy==5.1.*`, plus `pillow` for turnarounds):

- `glbstats.py <file.glb>`: prints triangle counts, materials, bones and animations
  from a glTF binary without opening Blender.
- `inspect_model.py -- <out.blend> <file.glb>`: imports the model, prints every bone's
  position and the model's height, and saves a .blend.
- `bake.py -- <import.blend> <triangles> <out.blend> <texture folder>`: makes a reduced
  copy of every mesh within its share of the triangle budget, gives it fresh UVs and
  bakes the full-quality colours onto it. The strand fur is left out, but its colour is
  baked into the suit. The slippers are rebuilt as one shell and the briefs are welded
  first, since both are made of many loose pieces.
- `fix_layers.py -- <in.blend> <out.blend>`: pushes outer clothing (the briefs) slightly
  outward so it doesn't cut into the layers beneath.
- `turnaround.py -- <in.blend> <out.png>`: renders front, three-quarter, side and back views.
- `export_glb.py -- <in.blend> <out.glb>`: exports the model, rig and animations to a glTF binary.
- `smanim.py`: Super Mario 64 animation maths matching sm64coopdx's renderer, and a reader
  for Mario's animations from your own ROM (located through an sm64coopdx checkout).
- `build_rig.py -- <cow_low.blend> <sm64coopdx dir> <rom> <height vs Mario> <out.blend> <out.json>`:
  fits her to Mario's 20 joints. Each joint takes Mario's A-pose orientation turned to match
  her bone, so Mario's animations bend her the right way, and the joint offsets come from her
  own bone lengths. Every vertex follows one joint, as on the N64.
- `pose_test.py -- <rig.blend> <rig.json> <sm64coopdx dir> <rom> <out.png> <anim:frame:label> ...`:
  renders her in poses from Mario's animations, using the game's joint maths.

The ROM is only read on your machine to pose her. No data from the ROM is written to this repo.

Example:

```bash
python -I tools/inspect_model.py -- work/cow_import.blend The_Misanthropic_Cow.glb
python -I tools/bake.py -- work/cow_import.blend 20000 work/cow_low.blend work/tex
python -I tools/fix_layers.py -- work/cow_low.blend work/cow_low.blend
python -I tools/turnaround.py -- work/cow_low.blend renders/cow_low_turnaround.png
python -I tools/build_rig.py -- work/cow_low.blend sm64coopdx baserom.us.z64 1.3 work/cow_sm.blend work/cow_sm.json
python -I tools/pose_test.py -- work/cow_sm.blend work/cow_sm.json sm64coopdx baserom.us.z64 renders/poses.png "anim_72:18:Running"
```
