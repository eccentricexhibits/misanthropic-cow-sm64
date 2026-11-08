"""Convert her glTF animations into Super Mario 64 animations for her 20-joint rig.

Usage: python -I convert_anims.py -- <cow_low.blend> <rig.json> <out anims.json>

Each joint follows the bone that drives it (rig.json 'driver_bones'): the joint's
frame is turned by the same rotation her bone makes away from its rest pose.
Rotations are then made relative to the parent joint and stored as the game's
XYZ angles. The root also stores her hip position, so the animation's
translation divisor is her hip height (the Lua sets the player's to match).
"""
import bpy, sys, json, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import smanim as sa

blend, rig_json, out = sys.argv[-3:]
R = json.load(open(rig_json)); s = R['scale_units_per_m']
names, parents, offsets = R['joints'], R['parents'], R['offsets']
F = {n: np.array(R['frames'][n]) for n in names}
driver = R['driver_bones']; H = R['hip_height']
P = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)

# name in the mod, her source animation(s), loops?
ANIMS = [
    ('cow_idle',    ['Idle'],                    False),
    ('cow_walk',    ['Walk'],                    True),
    ('cow_run',     ['Run'],                     True),
    ('cow_sneak',   ['Sneak'],                   True),
    ('cow_jump',    ['Jump Start', 'Jump Rise'], False),
    ('cow_fall',    ['Fall'],                    True),
    ('cow_land',    ['Land'],                    False),
    ('cow_skid',    ['Skid (game)'],             False),
    ('cow_hurt',    ['Hurt'],                    False),
    ('cow_death',   ['Death (game)'],            False),
    ('cow_victory', ['Victory'],                 False),
]
FPS = 30

bpy.ops.wm.open_mainfile(filepath=blend)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
arm.data.pose_position = 'POSE'
sc = bpy.context.scene; scene_fps = sc.render.fps / sc.render.fps_base
if arm.animation_data is None: arm.animation_data_create()
def game_rot(M4):           # blender armature-space 4x4 -> game column rotation
    Rb = np.array([[M4[r][c] for c in range(3)] for r in range(3)])
    Rb = Rb / np.linalg.norm(Rb, axis=0)       # drop any scale
    return P.T @ Rb @ P
def game_pos(M4): return s * (P.T @ np.array([M4[0][3], M4[1][3], M4[2][3]]))
rest = {b.name: game_rot(arm.matrix_world @ b.matrix_local) for b in arm.data.bones}

def sample(action_name):
    act = bpy.data.actions[action_name]
    arm.animation_data.action = act
    if hasattr(arm.animation_data, 'action_slot') and act.slots:
        arm.animation_data.action_slot = act.slots[0]
    f0, f1 = act.frame_range
    n = max(1, int(round((f1 - f0) / scene_fps * FPS)))
    frames = []
    for i in range(n):
        f = f0 + i * scene_fps / FPS
        sc.frame_set(int(np.floor(f)), subframe=float(f - np.floor(f)))
        pose = {}
        for bn in set(driver.values()):
            pb = arm.pose.bones[bn]; M = arm.matrix_world @ pb.matrix
            pose[bn] = (game_rot(M), game_pos(M))
        frames.append(pose)
    return frames

def to_channels(pose):
    """63 channel values (s16) for one frame."""
    world = {}
    vals = []
    for j, n in enumerate(names):
        Rt, _ = pose[driver[n]]
        D = Rt @ rest[driver[n]].T                     # her bone's rotation away from rest (column)
        world[n] = F[n] @ D.T                          # joint row matrix
        local = world[n] if parents[j] < 0 else world[n] @ world[names[parents[j]]].T
        if j == 0:
            hip = pose['Hips'][1]
            vals += [int(round(v)) for v in (hip - np.array(offsets[0], float))]
        rx, ry, rz = sa.euler_from_rot(local)
        vals += [int(round(a / sa.ANGLE)) for a in (rx, ry, rz)]
    return vals

def pack(channels):
    """channels: frames x 63 ints -> (values u16 list, index u16 list), constant channels stored once."""
    C = np.array(channels); values, index = [], []
    for c in range(C.shape[1]):
        col = C[:, c]
        if c >= 3: col = ((col + 32768) % 65536) - 32768
        if np.all(col == col[0]): col = col[:1]
        index += [len(col), len(values)]
        values += [int(v) & 0xFFFF for v in col]
    return values, index

result = {}
for name, srcs, loops in ANIMS:
    chans = []
    for src in srcs:
        chans += [to_channels(p) for p in sample(src)]
    values, index = pack(chans)
    result[name] = {'source': srcs, 'flags': 0 if loops else 1, 'divisor': int(round(H)),
                    'start': 0, 'loop_start': 0, 'loop_end': len(chans), 'values': values, 'index': index}
    print(f'{name:12} {len(chans):4} frames  {len(values):6} values  from {srcs}', flush=True)
json.dump(result, open(out, 'w'))
