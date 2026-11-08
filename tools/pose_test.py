"""Render the fitted model in poses from Mario's animations, using the game's joint maths.

Usage: python -I pose_test.py -- <cow_sm.blend> <cow_sm.json> <coopdx dir> <rom> <out.png> [--anims her_anims.json] <anim:frame:label> ...
Only her model is rendered; Mario's animation data is read from the ROM and not saved.
"""
import bpy, sys, json, os, math, tempfile
import numpy as np
from mathutils import Matrix
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smanim as sa
argv = sys.argv[sys.argv.index('--') + 1:]
blend, js, coopdx, rom, out = argv[:5]; rest = argv[5:]
extra = {}
if rest and rest[0] == '--anims':
    for k, a in json.load(open(rest[1])).items():
        extra[k] = sa.Anim(k, a['flags'], a['divisor'], a['start'], a['loop_start'], a['loop_end'], a['values'], a['index'])
    rest = rest[2:]
shots = [a.split(':', 2) for a in rest]
bpy.ops.wm.open_mainfile(filepath=blend)
J = json.load(open(js)); s = J['scale_units_per_m']; H = J['hip_height']
P = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)
def to_blender(W):
    M = Matrix.Identity(4); Rb = P @ W[:3, :3].T @ P.T; t = P @ W[3, :3] / s
    for r in range(3):
        for c in range(3): M[r][c] = Rb[r, c]
        M[r][3] = t[r]
    return M
A = sa.load_mario_anims(coopdx, rom); A.update(extra)
rig = bpy.data.objects['sm_rig']
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 16; sc.cycles.use_denoising = True
sc.render.resolution_x = 600; sc.render.resolution_y = 760
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.55, 0.62, 0.72, 1); bg.inputs[1].default_value = 0.8
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3
sun.rotation_euler = (math.radians(50), 0, math.radians(30)); sc.collection.objects.link(sun)
floor = bpy.data.meshes.new('floor'); floor.from_pydata([(-3,-3,0),(3,-3,0),(3,3,0),(-3,3,0)], [], [(0,1,2,3)])
fo = bpy.data.objects.new('floor', floor); sc.collection.objects.link(fo)
fm = bpy.data.materials.new('floor'); fm.use_nodes = True; fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (0.35, 0.38, 0.42, 1)
floor.materials.append(fm)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.3
sc.collection.objects.link(cam); sc.camera = cam
r = 6; ang = math.radians(-35)
cam.location = (-r * math.sin(ang), -r * math.cos(ang), 0.95 + r * math.cos(math.radians(80)))
cam.rotation_euler = (math.radians(80), 0, -ang)
tiles = []
for name, frame, label in shots:
    W = sa.evaluate(A[name], int(frame), J['offsets'], trans_mult=H / A[name].divisor)
    for n, Wj in zip(J['joints'], W): rig.pose.bones[n].matrix = to_blender(Wj)
    bpy.context.view_layer.update()
    p = os.path.join(tempfile.gettempdir(), f'pose_{name}_{frame}.png'); sc.render.filepath = p
    bpy.ops.render.render(write_still=True)
    im = Image.open(p).convert('RGB'); d = ImageDraw.Draw(im); d.rectangle([0, 0, 600, 34], fill=(40, 44, 52))
    d.text((12, 10), label, fill=(240, 240, 240)); tiles.append(im); os.remove(p)
cols = min(4, len(tiles)); rows = (len(tiles) + cols - 1) // cols
grid = Image.new('RGB', (600 * cols, 760 * rows), (40, 44, 52))
for i, t in enumerate(tiles): grid.paste(t, (600 * (i % cols), 760 * (i // cols)))
grid.save(out)
