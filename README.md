# The Misanthropic Cow for sm64coopdx

A mod that adds The Misanthropic Cow as a playable character in
[sm64coopdx](https://github.com/coop-deluxe/sm64coopdx), the PC version of Super Mario 64.
She uses her own animations where they fit (idle, walk, run, tiptoe, jump, fall,
land, skid, hurt, death, victory) and Mario's for every other action.

**This repo contains no game files.** To play, you need sm64coopdx installed with
your own copy of the game. Never add a ROM or anything extracted from one here.

## Status

| Step | State |
|---|---|
| Inspect the source model (1.4M triangles, 58 bones, 41 animations) | Done |
| First reduction to about 26k triangles, 512 px textures | Done (test) |
| Bake clean textures onto the reduced mesh; rebuild the slippers | Next |
| Rig to Mario's joint order, bones stretched to her height | To do |
| Convert her animations to the game's format | To do |
| Export the sm64coopdx mod (model + Lua) | To do |

## Tools

The scripts in `tools/` run with Blender 5.1 as a Python module (`pip install bpy==5.1.*`):

- `glbstats.py <file.glb>`: prints triangle counts, materials, bones and animations
  from a glTF binary without opening Blender.
- `inspect.py -- <out.blend> <file.glb>`: imports the model, prints every bone's
  position and the model's height, and saves a .blend.
- `reduce.py -- <in.blend> <triangles> <out.blend>`: removes the strand fur,
  reduces each mesh to its share of the triangle budget and shrinks textures to 512 px.
- `render.py -- <in.blend> <out.png>`: renders a quick preview with Cycles.

Example:

```bash
python -I tools/inspect.py -- work/cow_import.blend The_Misanthropic_Cow.glb
python -I tools/reduce.py -- work/cow_import.blend 20000 work/cow_20k.blend
python -I tools/render.py -- work/cow_20k.blend renders/cow_20k_test.png
```
