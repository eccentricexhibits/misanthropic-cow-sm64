"""Render a turnaround (front, 3/4, side, back) of a .blend at rest pose.
Usage: python -I turnaround.py -- <in.blend> <out.png>"""
import bpy, sys, math, os, tempfile
from PIL import Image
blend, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
for o in list(bpy.data.objects):
    if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE'); arm.data.pose_position = 'REST'; arm.animation_data_clear(); arm.rotation_mode = 'XYZ'
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.resolution_x = 640; sc.render.resolution_y = 1000
w = bpy.data.worlds.new('w'); sc.world = w; w.use_nodes = True
bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.55, 0.62, 0.72, 1); bg.inputs[1].default_value = 0.8
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); sun.data.energy = 3
sun.rotation_euler = (math.radians(50), 0, math.radians(30)); sc.collection.objects.link(sun)
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); cam.data.type = 'ORTHO'; cam.data.ortho_scale = 2.0
cam.location = (0, -6, 0.86); cam.rotation_euler = (math.radians(90), 0, 0); sc.collection.objects.link(cam); sc.camera = cam
tiles = []
for ang in (0, -40, -90, 180):
    arm.rotation_euler.z = math.radians(ang)
    p = os.path.join(tempfile.gettempdir(), f'ta_{ang}.png'); sc.render.filepath = p
    bpy.ops.render.render(write_still=True); tiles.append(Image.open(p).convert('RGB'))
W = sum(t.width for t in tiles); img = Image.new('RGB', (W, tiles[0].height))
x = 0
for t in tiles: img.paste(t, (x, 0)); x += t.width
img.save(out)
