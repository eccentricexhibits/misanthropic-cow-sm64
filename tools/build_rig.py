"""Fit the model to Mario's 20-joint skeleton, keeping her own proportions.

Usage: python -I build_rig.py -- <cow_low.blend> <coopdx dir> <rom> <height vs Mario> <out.blend> <out.json>

Each of Mario's joints gets a frame: Mario's A-pose orientation turned so the
bone points the way her bone points in her rest pose, placed at her joint.
Every vertex follows exactly one joint, as on the N64. Joint offsets come from
her bone lengths, so Mario's animations play on her real proportions.
The ROM is only read to get Mario's A-pose; nothing from it is saved.
"""
import bpy, sys, json, fnmatch, os
import numpy as np
from mathutils import Matrix
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smanim as sa

blend, coopdx, rom, k, out_blend, out_json = sys.argv[-6:]
k = float(k)
MARIO_HEIGHT = 620.0          # model units (about 155 game units after the 0.25 scale)
HER_HEIGHT_M = 1.71

bpy.ops.wm.open_mainfile(filepath=blend)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
arm.data.pose_position = 'REST'
s = k * MARIO_HEIGHT / HER_HEIGHT_M          # model units per metre
P = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)   # game -> blender axes
def g(v): return s * (P.T @ np.array(v, float))             # blender metres -> game units
B = {b.name: b for b in arm.data.bones}
head = lambda n: g(arm.matrix_world @ B[n].head_local)
tail = lambda n: g(arm.matrix_world @ B[n].tail_local)

# which joint each of her bones' vertices follow
VERT_MAP = [('Hips', 'butt'), ('Hem_*', 'butt'), ('Tail_*', 'butt'),
    ('Spine', 'torso'), ('Chest', 'torso'), ('Belly', 'torso'), ('Shag_*', 'torso'), ('Udder_*', 'torso'),
    ('Teat_*', 'torso'), ('Shoulder_?', 'torso'), ('Neck', 'head'), ('Head', 'head')]
for side in 'LR':
    sd = side.lower()
    VERT_MAP = [(f'Shag_elbow_{side}', f'{sd}_arm')] + VERT_MAP + [
        (f'UpperArm_{side}', f'{sd}_arm'), (f'UpperArmRoot_{side}', f'{sd}_arm'), (f'Elbow_{side}', f'{sd}_arm'),
        (f'Forearm_{side}', f'{sd}_forearm'), (f'Hand_{side}', f'{sd}_hand'), (f'HoofFingers_{side}', f'{sd}_hand'),
        (f'Thumb_{side}', f'{sd}_hand'), (f'HoofRingLittle_{side}', f'{sd}_hand'),
        (f'Thigh_{side}', f'{sd}_thigh'), (f'Shin_{side}', f'{sd}_leg'), (f'Foot_{side}', f'{sd}_foot')]
def joint_of(bone):
    for pat, j in VERT_MAP:
        if fnmatch.fnmatchcase(bone, pat): return j
    raise KeyError(bone)
# which of her bones drives each joint in her own animations
DRIVER = {'root': 'Hips', 'butt': 'Hips', 'torso': 'Chest', 'head': 'Head'}
for side in 'LR':
    sd = side.lower()
    DRIVER.update({f'{sd}_shoulder': 'Chest', f'{sd}_arm': f'UpperArm_{side}', f'{sd}_forearm': f'Forearm_{side}',
                   f'{sd}_hand': f'Hand_{side}', f'{sd}_hip': 'Hips', f'{sd}_thigh': f'Thigh_{side}',
                   f'{sd}_leg': f'Shin_{side}', f'{sd}_foot': f'Foot_{side}'})

# collect geometry: one vertex group per joint
names = [n for n, _ in sa.JOINTS]
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
verts_by_joint = {n: [] for n in names}
for o in meshes:
    for v in o.data.vertices:
        if not v.groups: continue
        gmax = max(v.groups, key=lambda e: e.weight)
        j = joint_of(o.vertex_groups[gmax.group].name)
        v_game = g(o.matrix_world @ v.co)
        verts_by_joint[j].append(v_game)

# pivots and directions in her rest pose
pivot, her_dir = {}, {}
pivot['root'] = pivot['butt'] = head('Hips')
pivot['torso'], pivot['head'] = head('Spine'), head('Neck')
her_dir['butt'] = head('Spine') - head('Hips'); her_dir['torso'] = head('Neck') - head('Spine')
her_dir['head'] = tail('Head') - head('Neck')
for side in 'LR':
    sd = side.lower()
    pivot[f'{sd}_shoulder'] = pivot[f'{sd}_arm'] = head(f'UpperArm_{side}')
    pivot[f'{sd}_forearm'], pivot[f'{sd}_hand'] = head(f'Forearm_{side}'), head(f'Hand_{side}')
    pivot[f'{sd}_hip'] = pivot[f'{sd}_thigh'] = head(f'Thigh_{side}')
    pivot[f'{sd}_leg'], pivot[f'{sd}_foot'] = head(f'Shin_{side}'), head(f'Foot_{side}')
    her_dir[f'{sd}_arm'] = head(f'Forearm_{side}') - head(f'UpperArm_{side}')
    her_dir[f'{sd}_forearm'] = head(f'Hand_{side}') - head(f'Forearm_{side}')
    her_dir[f'{sd}_hand'] = head(f'HoofFingers_{side}') - head(f'Hand_{side}')
    her_dir[f'{sd}_thigh'] = head(f'Shin_{side}') - head(f'Thigh_{side}')
    her_dir[f'{sd}_leg'] = head(f'Foot_{side}') - head(f'Shin_{side}')
    fv = np.array(verts_by_joint[f'{sd}_foot']); toe = fv[fv[:, 2] > np.percentile(fv[:, 2], 90)].mean(0)
    her_dir[f'{sd}_foot'] = toe - head(f'Foot_{side}')

# Mario's A-pose orientations (row matrices); only rotations are used
A = sa.load_mario_anims(coopdx, rom)
MOFF = [(0,0,0),(0,0,0),(68,0,0),(87,0,0),(67,-10,79),(0,0,0),(65,0,0),(60,0,0),(68,-10,-79),(0,0,0),(65,0,0),(60,0,0),
        (13,-8,42),(0,0,0),(89,0,0),(67,0,0),(13,-8,-42),(0,0,0),(89,0,0),(67,0,0)]
WM = sa.evaluate(A['anim_0E'], 0, MOFF)
def min_rot(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b); v = np.cross(a, b); c = a @ b
    if np.linalg.norm(v) < 1e-9: return np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)
F = {}
for j, n in enumerate(names):
    Rm = WM[j][:3, :3]
    if n in her_dir:
        Al = min_rot(Rm[0], her_dir[n])          # column-convention rotation, Mario dir -> her dir
        F[n] = Rm @ Al.T                          # row convention
    else:
        F[n] = Rm.copy()
# offsets in the parent's frame (row vectors: P_child = t @ F_parent + P_parent)
H = float(pivot['root'][1])
offsets = []
for j, (n, p) in enumerate(sa.JOINTS):
    if p < 0: t = pivot[n] - np.array([0, H, 0])
    else: t = (pivot[n] - pivot[names[p]]) @ F[names[p]].T
    offsets.append([round(float(x)) for x in t])
print('scale', round(s, 1), 'units/m   hip height H', round(H), '  Mario-anim translation x', round(H / 189, 3))
for (n, _), o in zip(sa.JOINTS, offsets): print(f'  {n:11} offset {o}  verts {len(verts_by_joint[n])}')

# armature for previews: one unparented bone per joint, rest = F, each vertex 100% one joint
def to_blender(R_row, t_game):
    M = Matrix.Identity(4); Rb = P @ R_row.T @ P.T
    for r in range(3):
        for c in range(3): M[r][c] = Rb[r, c]
        M[r][3] = (P @ np.asarray(t_game, float))[r] / s
    return M
rig = bpy.data.objects.new('sm_rig', bpy.data.armatures.new('sm_rig')); bpy.context.scene.collection.objects.link(rig)
bpy.context.view_layer.objects.active = rig; bpy.ops.object.mode_set(mode='EDIT')
for n in names:
    eb = rig.data.edit_bones.new(n); eb.head = (0, 0, 0); eb.tail = (0, 0.05, 0); eb.matrix = to_blender(F[n], pivot[n])
bpy.ops.object.mode_set(mode='OBJECT')
for o in meshes:
    weights = []
    for v in o.data.vertices:
        gmax = max(v.groups, key=lambda e: e.weight) if v.groups else None
        weights.append(joint_of(o.vertex_groups[gmax.group].name) if gmax else 'butt')
    o.vertex_groups.clear(); o.modifiers.clear(); o.parent = None
    for n in names: o.vertex_groups.new(name=n)
    for i, n in enumerate(weights): o.vertex_groups[n].add([i], 1.0, 'REPLACE')
    m = o.modifiers.new('sm', 'ARMATURE'); m.object = rig
bpy.data.objects.remove(arm)
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
json.dump({'scale_units_per_m': s, 'height_vs_mario': k, 'hip_height': H, 'joints': names,
           'parents': [p for _, p in sa.JOINTS], 'offsets': offsets,
           'frames': {n: F[n].tolist() for n in names}, 'pivots': {n: pivot[n].tolist() for n in names},
           'driver_bones': DRIVER}, open(out_json, 'w'), indent=1)
