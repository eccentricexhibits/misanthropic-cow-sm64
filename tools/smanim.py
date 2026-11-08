"""SM64 animation maths, matching sm64coopdx's renderer.

- Reads Mario's animations from the player's own ROM, using the table of ROM
  offsets in an sm64coopdx checkout (assets/anims/*.inc.c). The data is only
  used locally to pose the model; nothing read from the ROM is written to the repo.
- Evaluates an animation on a joint hierarchy with the same matrix maths as
  geo_process_animated_part (row vectors: world = local @ parent).
"""
import re, glob, os, struct
import numpy as np

ANGLE = 2 * np.pi / 65536.0

# Mario's 20 animated joints in geo traversal order: (name, parent index)
JOINTS = [
    ('root', -1), ('butt', 0), ('torso', 1), ('head', 2),
    ('l_shoulder', 2), ('l_arm', 4), ('l_forearm', 5), ('l_hand', 6),
    ('r_shoulder', 2), ('r_arm', 8), ('r_forearm', 9), ('r_hand', 10),
    ('l_hip', 1), ('l_thigh', 12), ('l_leg', 13), ('l_foot', 14),
    ('r_hip', 1), ('r_thigh', 16), ('r_leg', 17), ('r_foot', 18),
]
NJ = len(JOINTS)

class Anim:
    def __init__(self, name, flags, divisor, start, loop_start, loop_end, values, index):
        self.name, self.flags, self.divisor = name, flags, divisor
        self.start, self.loop_start, self.loop_end = start, loop_start, loop_end
        self.values = np.asarray(values, dtype=np.int64)   # raw u16
        self.index = np.asarray(index, dtype=np.int64)
    def channel(self, ch, frame):
        """Value of channel ch at frame, as retrieve_animation_value does (s16)."""
        i = 2 * ch
        if i + 1 >= len(self.index): return 0
        cnt, off = self.index[i], self.index[i + 1]
        k = off + frame if frame < cnt else off + cnt - 1
        k = max(0, min(k, len(self.values) - 1))
        v = int(self.values[k]); return v - 65536 if v >= 32768 else v
    @property
    def frames(self): return int(self.loop_end)

def load_mario_anims(coopdx_dir, rom_path):
    rom = open(rom_path, 'rb').read()
    def u16s(addr, size): return struct.unpack('>%dH' % (size // 2), rom[addr:addr + size])
    anims = {}
    for f in sorted(glob.glob(os.path.join(coopdx_dir, 'assets/anims/anim_*.inc.c'))):
        src = open(f).read()
        loads = {m[0]: (int(m[1], 16), int(m[2])) for m in
                 re.findall(r'ROM_ASSET_LOAD_ANIM\((\w+),\s*(0x[0-9a-fA-F]+),\s*(\d+)', src)}
        for m in re.finditer(r'static const struct Animation (anim_\w+)\[\] = \{(.*?)\};', src, re.S):
            name, body = m.group(1), m.group(2)
            parts = [p.strip() for p in body.split(',') if p.strip()]
            num = lambda s: int(s, 0)
            flags, div, start, ls, le = map(num, parts[:5])
            vname, iname = parts[6], parts[7]
            anims[name] = Anim(name, flags, div, start, ls, le, u16s(*loads[vname]), u16s(*loads[iname]))
    return anims

def rot_xyz(rx, ry, rz):
    """3x3 rotation exactly as mtxf_rotate_xyz_and_translate (angles in radians)."""
    sx, cx, sy, cy, sz, cz = np.sin(rx), np.cos(rx), np.sin(ry), np.cos(ry), np.sin(rz), np.cos(rz)
    return np.array([[cy*cz, cy*sz, -sy],
                     [sx*sy*cz - cx*sz, sx*sy*sz + cx*cz, sx*cy],
                     [cx*sy*cz + sx*sz, cx*sy*sz - sx*cz, cx*cy]])

def euler_from_rot(M):
    """Inverse of rot_xyz: returns (rx, ry, rz) in radians."""
    sy = -M[0, 2]; ry = np.arcsin(np.clip(sy, -1, 1))
    if abs(sy) < 0.99999:
        rx = np.arctan2(M[1, 2], M[2, 2]); rz = np.arctan2(M[0, 1], M[0, 0])
    else:  # gimbal lock: put everything in x
        rz = 0.0; rx = np.arctan2(-M[2, 1] if sy > 0 else M[2, 1], M[1, 1])
        if sy < 0: rx = np.arctan2(-M[1, 0], M[1, 1])
    return rx, ry, rz

def mat4(R, t):
    M = np.eye(4); M[:3, :3] = R; M[3, :3] = t; return M

def evaluate(anim, frame, offsets, trans_mult=1.0, parents=None):
    """World matrices (4x4, row-vector convention) of every joint at frame."""
    parents = parents or [p for _, p in JOINTS]
    n = len(offsets); world = [None] * n; ch = 0
    for j in range(n):
        t = np.array(offsets[j], dtype=float)
        if j == 0:
            t += np.array([anim.channel(c, frame) for c in range(3)]) * trans_mult; ch = 3
        r = [anim.channel(ch + c, frame) * ANGLE for c in range(3)]; ch += 3
        local = mat4(rot_xyz(*r), t)
        world[j] = local if parents[j] < 0 else local @ world[parents[j]]
    return world
