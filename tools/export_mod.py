"""Write the sm64coopdx mod: her model as DynOS source, textures, and the Lua scripts.

Usage: python -I export_mod.py -- <rig.blend> <rig.json> <anims.json> <out mod folder>

Model: one display list per joint, with vertices in that joint's own space.
Triangles that cross a joint seam (shoulder, elbow, hip, knee, neck, waist) use
vertices the parent joint loaded earlier into reserved slots of the renderer's
64-vertex buffer, so the seam stretches instead of tearing, the same technique
the game's own player model uses.
"""
import bpy, sys, os, json, math, shutil
import numpy as np
from PIL import Image

blend, rig_json, anims_json, out = sys.argv[-4:]
R = json.load(open(rig_json)); s = R['scale_units_per_m']
F = {n: np.array(R['frames'][n]) for n in R['joints']}
PIV = {n: np.array(R['pivots'][n]) for n in R['joints']}
OFF = dict(zip(R['joints'], R['offsets']))
P = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)
PREFIX = 'misanthropic_cow'
ACTOR = os.path.join(out, 'actors', PREFIX)
if os.path.isdir(out): shutil.rmtree(out)
os.makedirs(ACTOR)

# joints that carry geometry, in the order the game draws them, and their drawing parent
DLJ = ['butt', 'torso', 'head', 'l_arm', 'l_forearm', 'l_hand', 'r_arm', 'r_forearm', 'r_hand',
       'l_thigh', 'l_leg', 'l_foot', 'r_thigh', 'r_leg', 'r_foot']
DLP = {'torso': 'butt', 'head': 'torso', 'l_arm': 'torso', 'l_forearm': 'l_arm', 'l_hand': 'l_forearm',
       'r_arm': 'torso', 'r_forearm': 'r_arm', 'r_hand': 'r_forearm', 'l_thigh': 'butt', 'l_leg': 'l_thigh',
       'l_foot': 'l_leg', 'r_thigh': 'butt', 'r_leg': 'r_thigh', 'r_foot': 'r_leg'}
def ancestors(j):
    a = []
    while j in DLP: j = DLP[j]; a.append(j)
    return a
ORDER = {j: i for i, j in enumerate(DLJ)}
# Most seam vertices a joint may keep loaded for one child. The hip seams stay loaded
# while the whole upper body draws, so they get the smallest share of the 64 slots.
SEAM_CAP = {'l_thigh': 10, 'r_thigh': 10, 'l_arm': 12, 'r_arm': 12}
SEAM_CAP_DEFAULT = 16
# Parts moved to another joint to avoid long seams. The suit's lower edge already overlaps
# the briefs, so the whole suit rides on the torso and the waist needs no seam.
JOINT_OVERRIDE = {('Suit_torso', 'butt'): 'torso'}

bpy.ops.wm.open_mainfile(filepath=blend)
# ---- gather geometry ----
mats = {}      # material name -> (texture symbol, w, h)
verts = []     # dicts: joint, local pos, normal, s, t
vkey = {}
tris = []      # (material, [vertex ids])
for o in [o for o in bpy.data.objects if o.type == 'MESH']:
    me = o.data; me.calc_loop_triangles()
    mat = me.materials[0]
    if mat.name not in mats:
        img = next(n.image for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE')
        short = mat.name.replace('_LOW_mat', '').lower()
        for w in ('_white_faux_fur', '_black_cotton', '_pink_satin', '_cow_mule', '_gold_satin', '_pink_cloth_cup_and_teats'):
            short = short.replace(w, '')
        path = os.path.join(ACTOR, short + '.rgba16.png')
        px = np.array(img.pixels[:]).reshape(img.size[1], img.size[0], 4)[::-1]
        Image.fromarray((np.clip(px, 0, 1) * 255).astype(np.uint8), 'RGBA').save(path)
        mats[mat.name] = (f'{PREFIX}_tex_{short}', short, img.size[0], img.size[1])
    _, _, W, H = mats[mat.name]
    uv = me.uv_layers.active.data
    jname = {g.index: g.name for g in o.vertex_groups}
    vjoint = [jname[max(v.groups, key=lambda e: e.weight).group] for v in me.vertices]
    for (prefix, frm), to in JOINT_OVERRIDE.items():
        if o.name.startswith(prefix): vjoint = [to if j == frm else j for j in vjoint]
    M = o.matrix_world
    for lt in me.loop_triangles:
        ids = []
        for li, vi in zip(lt.loops, lt.vertices):
            u, v = uv[li].uv
            st = (int(round(u * W * 32)), int(round((1 - v) * H * 32)))
            key = (o.name, vi, st)
            if key not in vkey:
                j = vjoint[vi]
                pg = s * (P.T @ np.array(M @ me.vertices[vi].co))
                ng = P.T @ np.array((M.to_3x3() @ me.vertices[vi].normal).normalized())
                vkey[key] = len(verts)
                verts.append({'joint': j, 'pos': pg, 'n': ng, 'st': st, 'key': key})
            ids.append(vkey[key])
        tris.append((mat.name, ids))
print(len(verts), 'vertices', len(tris), 'triangles', len(mats), 'textures')

def local(vid, joint):
    v = verts[vid]
    p = (v['pos'] - PIV[joint]) @ F[joint].T
    n = v['n'] @ F[joint].T
    return [int(round(x)) for x in p], [int(round(max(-1, min(1, x)) * 127)) for x in n]

# ---- assign triangles to joints and collect seam vertices ----
owned = {j: [] for j in DLJ}          # joint -> list of (material, [refs]); ref = ('own', vid, joint) or ('seam', anc, vid)
seam_need = {}                         # (ancestor, consumer) -> ordered vertex ids
dups = 0
for m, ids in tris:
    js = [verts[i]['joint'] for i in ids]
    deep = max(js, key=lambda j: ORDER[j])
    if all(j == deep or j in ancestors(deep) for j in js):
        refs = []
        for i, j in zip(ids, js):
            if j == deep: refs.append(('own', i))
            else:
                lst = seam_need.setdefault((j, deep), [])
                if i not in lst: lst.append(i)
                refs.append(('seam', j, i))
        owned[deep].append((m, refs))
    else:   # joints that aren't in one chain: copy the vertex into the owner's space (may open a small gap)
        owner = max(set(js), key=js.count); dups += 1
        owned[owner].append((m, [('own', i) if j == owner else ('dup', i) for i, j in zip(ids, js)]))
# cap seams, keeping the vertices most triangles use; the rest become copies in the child's space
print('seam vertices before caps:', {f'{a}->{c}': len(v) for (a, c), v in seam_need.items()})
for k, lst in seam_need.items():
    cap = SEAM_CAP.get(k[1], SEAM_CAP_DEFAULT)
    if len(lst) > cap:
        use = {}
        for tri in owned[k[1]]:
            for r in tri[1]:
                if r[0] == 'seam' and r[1] == k[0]: use[r[2]] = use.get(r[2], 0) + 1
        lst.sort(key=lambda i: -use.get(i, 0))
        keep = set(lst[:cap]); anc, cons = k
        for tri in owned[cons]:
            tri[1][:] = [('dup', r[2]) if r[0] == 'seam' and r[1] == anc and r[2] not in keep else r for r in tri[1]]
        seam_need[k] = lst[:cap]
print('seams:', {f'{a}->{c}': len(v) for (a, c), v in seam_need.items()}, ' cross-chain triangles:', dups)

# ---- slot allocation and display lists ----
slots = [None] * 64
reserved = {}        # (anc, consumer) -> start slot
def alloc(n, tag):
    for st in range(0, 64 - n + 1):
        if all(slots[st + k] is None for k in range(n)):
            for k in range(n): slots[st + k] = tag
            return st
    raise RuntimeError('vertex buffer full')
def vtx_line(p, st, nrm):
    return '    {{{%d, %d, %d}, 0, {%d, %d}, {%d, %d, %d, 0xFF}}},' % (*p, *st, *nrm)
C = []   # model.inc.c chunks
C.append(f'// The Misanthropic Cow: model for sm64coopdx (generated by tools/export_mod.py)\n')
C.append(f'static const Lights1 {PREFIX}_lights = gdSPDefLights1(0x66, 0x66, 0x66, 0xFF, 0xFF, 0xFF, 0x28, 0x28, 0x28);\n')
for mname, (sym, short, W, H) in mats.items():
    C.append(f'ALIGNED8 static const Texture {sym}[] = {{\n#include "actors/{PREFIX}/{short}.rgba16.inc.c"\n}};\n')
stats = {}
for j in DLJ:
    lines = [f'const Gfx {PREFIX}_{j}_dl[] = {{', '    gsDPPipeSync(),',
             '    gsDPSetCombineMode(G_CC_MODULATERGB, G_CC_MODULATERGB),',
             '    gsSPClearGeometryMode(G_CULL_BACK),', '    gsSPSetGeometryMode(G_LIGHTING | G_SHADE),',
             f'    gsSPSetLights1({PREFIX}_lights),', '    gsSPTexture(0xFFFF, 0xFFFF, 0, G_TX_RENDERTILE, G_ON),']
    arrays = []
    def fixed_slot(ref):
        if ref[0] == 'seam': return reserved[(ref[1], j)] + seam_need[(ref[1], j)].index(ref[2])
        return None
    # 2. working space: the largest free run
    free_runs, st = [], None
    for k in range(65):
        if k < 64 and slots[k] is None:
            st = k if st is None else st
        elif st is not None: free_runs.append((k - st, st)); st = None
    wn, ws = max(free_runs); wn = min(wn, 32)
    stats[j] = {'working_slots': wn}
    # 3. draw triangles, grouped by material, in batches that fit the working space
    batch_no = 0
    for mname, (sym, short, W, H) in mats.items():
        mt = [r for m, r in owned[j] if m == mname]
        if not mt: continue
        lines.append(f'    gsDPLoadTextureBlock({sym}, G_IM_FMT_RGBA, G_IM_SIZ_16b, {W}, {H}, 0, '
                     f'G_TX_WRAP | G_TX_NOMIRROR, G_TX_WRAP | G_TX_NOMIRROR, {int(math.log2(W))}, {int(math.log2(H))}, G_TX_NOLOD, G_TX_NOLOD),')
        # order triangles so neighbours come together
        todo = list(range(len(mt))); order = []; adj = {}
        for ti, refs in enumerate(mt):
            for r in refs: adj.setdefault(r[-1], []).append(ti)
        done = set()
        while todo:
            seed = next(t for t in todo if t not in done); queue = [seed]
            while queue:
                t = queue.pop(0)
                if t in done: continue
                done.add(t); order.append(t)
                for r in mt[t]:
                    queue += [u for u in adj[r[-1]] if u not in done]
            todo = [t for t in todo if t not in done]
        batch, btris = [], []
        def flush():
            global batch_no
            if not btris: return
            name = f'{PREFIX}_{j}_vtx_{batch_no}'; batch_no += 1
            body = []
            for ref in batch:
                kind, i = ref[0], ref[-1]
                p, n = local(i, j)
                body.append(vtx_line(p, verts[i]['st'], n))
            arrays.append(f'static const Vtx {name}[] = {{\n' + '\n'.join(body) + '\n};\n')
            lines.append(f'    gsSPVertex({name}, {len(batch)}, {ws}),')
            for a in range(0, len(btris), 2):
                t1 = btris[a]
                if a + 1 < len(btris): lines.append('    gsSP2Triangles(%d, %d, %d, 0x0, %d, %d, %d, 0x0),' % (*t1, *btris[a + 1]))
                else: lines.append('    gsSP1Triangle(%d, %d, %d, 0x0),' % t1)
            batch.clear(); btris.clear()
        for t in order:
            refs = mt[t]
            new = [r for r in refs if fixed_slot(r) is None and r not in batch]
            new = list(dict.fromkeys(new))
            if len(batch) + len(new) > wn: flush(); new = list(dict.fromkeys(r for r in refs if fixed_slot(r) is None))
            batch.extend(new)
            btris.append(tuple(fixed_slot(r) if fixed_slot(r) is not None else ws + batch.index(r) for r in refs))
        flush()
    # 4. free the seams this joint used, then load the seam vertices its children will use
    for k in [k for k in reserved if k[1] == j]:
        slots[:] = [None if x == k else x for x in slots]
    for (anc, cons), lst in seam_need.items():
        if anc != j or not lst: continue
        st = alloc(len(lst), (anc, cons)); reserved[(anc, cons)] = st
        name = f'{PREFIX}_{j}_seam_{cons}_vtx'; body = []
        for i in lst:
            p, n = local(i, j); body.append(vtx_line(p, verts[i]['st'], n))
        arrays.append(f'static const Vtx {name}[] = {{\n' + '\n'.join(body) + '\n};\n')
        lines.append(f'    gsSPVertex({name}, {len(lst)}, {st}),')
    lines += ['    gsSPEndDisplayList(),', '};\n']
    C += arrays; C.append('\n'.join(lines))
C.append(f'''const Gfx {PREFIX}_material_revert_render_settings[] = {{
    gsDPPipeSync(),
    gsSPSetGeometryMode(G_LIGHTING | G_CULL_BACK),
    gsSPTexture(0xFFFF, 0xFFFF, 0, G_TX_RENDERTILE, G_OFF),
    gsDPSetCombineMode(G_CC_SHADE, G_CC_SHADE),
    gsSPEndDisplayList(),
}};
''')
open(os.path.join(ACTOR, 'model.inc.c'), 'w').write('\n'.join(C))
print('working slots per joint:', {j: v['working_slots'] for j, v in stats.items()})

# ---- geo layout ----
o = lambda n: '%d, %d, %d' % tuple(OFF[n])
def hand(side):
    sd = side[0]; dl = f'{PREFIX}_{sd}_hand_dl'; idx = 1 if side == 'left' else 0
    held = '\n         GEO_HELD_OBJECT(0x00, 0, 0, 0, geo_switch_mario_hand_grab_pos),' if side == 'right' else ''
    cases = [f'''   GEO_ANIMATED_PART(LAYER_OPAQUE, {o(sd + "_hand")}, NULL),
   GEO_OPEN_NODE(),
      GEO_ASM({idx}, geo_mario_hand_foot_scaler),
      GEO_SCALE(0x00, 65536),
      GEO_OPEN_NODE(),
         GEO_DISPLAY_LIST(LAYER_OPAQUE, {dl}),{held}
      GEO_CLOSE_NODE(),
   GEO_CLOSE_NODE(),''']
    for k in range(4):
        c = f'   GEO_ANIMATED_PART(LAYER_OPAQUE, {o(sd + "_hand")}, {dl}),'
        if side == 'right' and k == 0:
            c += '\n   GEO_OPEN_NODE(),\n      GEO_HELD_OBJECT(0x00, 0, 0, 0, geo_switch_mario_hand_grab_pos),\n   GEO_CLOSE_NODE(),'
        cases.append(c)
    body = '\n'.join(c.replace('\n', '\n   ') for c in cases)
    return f'''const GeoLayout {PREFIX}_geo_{side}_hand[] = {{
   GEO_SWITCH_CASE({idx}, geo_switch_mario_hand),
   GEO_OPEN_NODE(),
   {body}
   GEO_CLOSE_NODE(),
   GEO_RETURN(),
}};
'''
def leg(sd, right):
    foot = (f'''                  GEO_ANIMATED_PART(LAYER_OPAQUE, {o(sd + "_foot")}, NULL),
                  GEO_OPEN_NODE(),
                     GEO_ASM(2, geo_mario_hand_foot_scaler),
                     GEO_SCALE(0x00, 65536),
                     GEO_OPEN_NODE(),
                        GEO_DISPLAY_LIST(LAYER_OPAQUE, {PREFIX}_{sd}_foot_dl),
                     GEO_CLOSE_NODE(),
                  GEO_CLOSE_NODE(),''' if right else
            f'                  GEO_ANIMATED_PART(LAYER_OPAQUE, {o(sd + "_foot")}, {PREFIX}_{sd}_foot_dl),')
    return f'''      GEO_ANIMATED_PART(LAYER_OPAQUE, {o(sd + "_hip")}, NULL),
      GEO_OPEN_NODE(),
         GEO_ANIMATED_PART(LAYER_OPAQUE, {o(sd + "_thigh")}, {PREFIX}_{sd}_thigh_dl),
         GEO_OPEN_NODE(),
            GEO_ANIMATED_PART(LAYER_OPAQUE, {o(sd + "_leg")}, {PREFIX}_{sd}_leg_dl),
            GEO_OPEN_NODE(),
{foot}
            GEO_CLOSE_NODE(),
         GEO_CLOSE_NODE(),
      GEO_CLOSE_NODE(),'''
def arm(sd, side):
    return f'''               GEO_ANIMATED_PART(LAYER_OPAQUE, {o(sd + "_shoulder")}, NULL),
               GEO_OPEN_NODE(),
                  GEO_ANIMATED_PART(LAYER_OPAQUE, {o(sd + "_arm")}, {PREFIX}_{sd}_arm_dl),
                  GEO_OPEN_NODE(),
                     GEO_ANIMATED_PART(LAYER_OPAQUE, {o(sd + "_forearm")}, {PREFIX}_{sd}_forearm_dl),
                     GEO_OPEN_NODE(),
                        GEO_BRANCH(1, {PREFIX}_geo_{side}_hand),
                     GEO_CLOSE_NODE(),
                  GEO_CLOSE_NODE(),
               GEO_CLOSE_NODE(),'''
LAY = ['LAYER_OPAQUE', 'LAYER_ALPHA', 'LAYER_TRANSPARENT']
geo = f'''// The Misanthropic Cow: node layout for sm64coopdx (generated by tools/export_mod.py).
// Joints follow the order the game's player animations expect.

const GeoLayout {PREFIX}_geo_face[] = {{
   GEO_ASM(0, geo_mario_head_rotation),
   GEO_ROTATION_NODE(0x00, 0, 0, 0),
   GEO_OPEN_NODE(),
      GEO_DISPLAY_LIST(LAYER_OPAQUE, {PREFIX}_head_dl),
   GEO_CLOSE_NODE(),
   GEO_RETURN(),
}};

{hand("left")}
{hand("right")}
const GeoLayout {PREFIX}_geo_body[] = {{
   GEO_ANIMATED_PART(LAYER_OPAQUE, {o("root")}, NULL),
   GEO_OPEN_NODE(),
   GEO_ANIMATED_PART(LAYER_OPAQUE, {o("butt")}, {PREFIX}_butt_dl),
   GEO_OPEN_NODE(),
      GEO_ASM(0, geo_move_mario_part_from_parent),
      GEO_ASM(0, geo_mario_tilt_torso),
      GEO_ROTATION_NODE(0x00, 0, 0, 0),
      GEO_OPEN_NODE(),
         GEO_ANIMATED_PART(LAYER_OPAQUE, {o("torso")}, {PREFIX}_torso_dl),
         GEO_OPEN_NODE(),
            GEO_ANIMATED_PART(LAYER_OPAQUE, {o("head")}, NULL),
            GEO_OPEN_NODE(),
               GEO_BRANCH(1, {PREFIX}_geo_face),
            GEO_CLOSE_NODE(),
{arm("l", "left")}
{arm("r", "right")}
         GEO_CLOSE_NODE(),
      GEO_CLOSE_NODE(),
{leg("l", False)}
{leg("r", True)}
   GEO_CLOSE_NODE(),
   GEO_CLOSE_NODE(),
   GEO_RETURN(),
}};

const GeoLayout {PREFIX}_geo_load_body[] = {{
   GEO_SWITCH_CASE(0, geo_switch_mario_cap_effect),
   GEO_OPEN_NODE(),
      GEO_BRANCH(1, {PREFIX}_geo_body),
      GEO_BRANCH(1, {PREFIX}_geo_body),
      GEO_BRANCH(1, {PREFIX}_geo_body),
      GEO_BRANCH(1, {PREFIX}_geo_body),
   GEO_CLOSE_NODE(),
   GEO_RETURN(),
}};

const GeoLayout {PREFIX}_geo[] = {{
   GEO_NODE_START(),
   GEO_OPEN_NODE(),
      GEO_SHADOW(SHADOW_CIRCLE_PLAYER, 0xB4, 130),
      GEO_OPEN_NODE(),
         GEO_SCALE(0x00, 16384),
         GEO_OPEN_NODE(),
{chr(10).join(f"            GEO_ASM({l} + 3, geo_mario_set_player_colors)," for l in LAY)}
{chr(10).join(f"            GEO_ASM({l} << 2, geo_mirror_mario_backface_culling)," for l in LAY)}
            GEO_ASM(0, geo_mirror_mario_set_alpha),
            GEO_OPEN_NODE(),
               GEO_BRANCH(1, {PREFIX}_geo_load_body),
            GEO_CLOSE_NODE(),
{chr(10).join(f"            GEO_ASM(({l} << 2) | 1, geo_mirror_mario_backface_culling)," for l in LAY)}
         GEO_CLOSE_NODE(),
      GEO_CLOSE_NODE(),
      GEO_DISPLAY_LIST(LAYER_OPAQUE, {PREFIX}_material_revert_render_settings),
   GEO_CLOSE_NODE(),
   GEO_END(),
}};
'''
open(os.path.join(ACTOR, 'geo.inc.c'), 'w').write(geo)

# ---- Lua ----
A = json.load(open(anims_json))
with open(os.path.join(out, 'animations.lua'), 'w') as f:
    f.write('-- Her animations in the game\'s format (generated by tools/export_mod.py from her own glTF animations).\n\n')
    for name, a in A.items():
        def tbl(xs): return '{' + ','.join(str(x) for x in xs) + '}'
        f.write(f'smlua_anim_util_register_animation("{name}", {a["flags"]}, {a["divisor"]}, {a["start"]}, '
                f'{a["loop_start"]}, {a["loop_end"]},\n    {tbl(a["values"])},\n    {tbl(a["index"])})\n\n')
HIP = int(round(R['hip_height']))
main = f'''-- name: The Misanthropic Cow
-- description: Play as The Misanthropic Cow, with her own idle, walk, run, sneak, jump, fall, landing, skid, hurt, death and victory animations.\\n\\nType /cow to switch her on or off.

-- Her model (built from actors/{PREFIX}/)
local E_MODEL_COW = smlua_model_util_get_id("{PREFIX}_geo")

-- Her hip height in model units. The game scales its animations' body movement by this,
-- so Mario's animations fit her longer legs and her own animations play at their real size.
local COW_HIP_HEIGHT = {HIP}
local DEFAULT_HIP_HEIGHT = 189

-- Which of the game's animations she replaces with her own
local REPLACE = {{
    [MARIO_ANIM_IDLE_HEAD_LEFT]         = "cow_idle",
    [MARIO_ANIM_IDLE_HEAD_RIGHT]        = "cow_idle",
    [MARIO_ANIM_IDLE_HEAD_CENTER]       = "cow_idle",
    [MARIO_ANIM_WALKING]                = "cow_walk",
    [MARIO_ANIM_RUNNING]                = "cow_run",
    [MARIO_ANIM_TIPTOE]                 = "cow_sneak",
    [MARIO_ANIM_START_TIPTOE]           = "cow_sneak",
    [MARIO_ANIM_SINGLE_JUMP]            = "cow_jump",
    [MARIO_ANIM_GENERAL_FALL]           = "cow_fall",
    [MARIO_ANIM_LAND_FROM_SINGLE_JUMP]  = "cow_land",
    [MARIO_ANIM_GENERAL_LAND]           = "cow_land",
    [MARIO_ANIM_SKID_ON_GROUND]         = "cow_skid",
    [MARIO_ANIM_SOFT_BACK_KB]           = "cow_hurt",
    [MARIO_ANIM_SOFT_FRONT_KB]          = "cow_hurt",
    [MARIO_ANIM_DYING_ON_BACK]          = "cow_death",
    [MARIO_ANIM_DYING_ON_STOMACH]       = "cow_death",
    [MARIO_ANIM_DYING_FALL_OVER]        = "cow_death",
    [MARIO_ANIM_STAR_DANCE]             = "cow_victory",
}}

for i = 0, MAX_PLAYERS - 1 do
    gPlayerSyncTable[i].cowOn = true
end

local function mario_update(m)
    local o = m.marioObj
    if gPlayerSyncTable[m.playerIndex].cowOn then
        obj_set_model_extended(o, E_MODEL_COW)
        m.unkB0 = COW_HIP_HEIGHT
        o.header.gfx.animInfo.animYTrans = COW_HIP_HEIGHT
        local name = REPLACE[o.header.gfx.animInfo.animID]
        if name ~= nil then
            smlua_anim_util_set_animation(o, name)
        end
    elseif m.unkB0 == COW_HIP_HEIGHT then
        m.unkB0 = DEFAULT_HIP_HEIGHT
        o.header.gfx.animInfo.animYTrans = DEFAULT_HIP_HEIGHT
    end
end

local function on_cow_command(msg)
    local s = gPlayerSyncTable[0]
    if msg == "on" then s.cowOn = true
    elseif msg == "off" then s.cowOn = false
    else s.cowOn = not s.cowOn end
    djui_chat_message_create(s.cowOn and "The Misanthropic Cow: on" or "The Misanthropic Cow: off")
    return true
end

hook_event(HOOK_MARIO_UPDATE, mario_update)
hook_chat_command("cow", "[on|off] - play as The Misanthropic Cow", on_cow_command)
'''
open(os.path.join(out, 'main.lua'), 'w').write(main)
print('wrote', out)
