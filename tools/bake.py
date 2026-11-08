"""Build a reduced copy of every mesh and bake the full-quality colours onto it.
Usage: python -I bake.py -- <import.blend> <triangle budget> <out.blend> <texdir>"""
import bpy, bmesh, sys, os, time
src, budget, out, texdir = sys.argv[-4], int(sys.argv[-3]), sys.argv[-2], sys.argv[-1]
os.makedirs(texdir, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=src)
for o in list(bpy.data.objects):
    if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
arm.data.pose_position = 'REST'
# share of the budget, texture size, extra bake sources
W = {'Suit_torso':(25,512,'shag'),'Mask_scanned_face':(12,512,''),'Slipper_L':(4,256,''),'Slipper_R':(4,256,''),
     'Briefs':(4,256,''),'Glove_L_palm':(3,256,''),'Glove_R_palm':(3,256,''),'Glove_L_toe':(1,128,''),'Glove_R_toe':(1,128,''),
     'Leggings_L':(4,256,''),'Leggings_R':(4,256,''),'Leggings_seat':(2,128,''),'Udder_L':(3,256,''),'Udder_R':(3,256,''),
     'Suit_sleeve_L':(3,256,'shag'),'Suit_sleeve_R':(3,256,'shag'),'Hood':(4,256,''),'Horn':(1.2,128,''),
     'Tail_gold':(1.5,128,''),'Mask_lower_jaw':(1.5,128,''),'Tail_plug_body':(0.8,64,''),'Mask_horn_tube':(0.7,128,''),
     'Tail_lamp_cord':(0.6,64,''),'Tail_plug_brass':(0.4,64,'')}
REMESH = ('Slipper_',)   # many loose pieces: rebuild as one shell first
WELD = ('Briefs',)       # thin cloth split into loose triangles: weld it back together
def spec(n):
    for k, v in W.items():
        if n.startswith(k): return v
highs = [o for o in bpy.data.objects if o.type == 'MESH']
shag = [o for o in highs if o.name.startswith('Suit_black_shag')]
targets = [o for o in highs if spec(o.name)]
tot_w = sum(spec(o.name)[0] for o in targets)
sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 4
bk = sc.render.bake; bk.use_selected_to_active = True; bk.use_pass_direct = False; bk.use_pass_indirect = False
bk.use_pass_color = True; bk.margin = 16; bk.margin_type = 'EXTEND'
low_coll = bpy.data.collections.new('LOW'); sc.collection.children.link(low_coll)
total = 0
for hi in targets:
    t0 = time.time(); w, tex, extra = spec(hi.name)
    if hi.data.shape_keys: hi.shape_key_clear()
    lo = hi.copy(); lo.data = hi.data.copy(); lo.name = hi.name.split('.')[0] + '_LOW'; low_coll.objects.link(lo)
    for m in list(lo.modifiers):
        if m.type != 'ARMATURE': lo.modifiers.remove(m)
    def apply(mod):
        lo.modifiers.move(len(lo.modifiers)-1, 0)
        with bpy.context.temp_override(object=lo, active_object=lo): bpy.ops.object.modifier_apply(modifier=mod.name)
    if hi.name.startswith(REMESH):
        r = lo.modifiers.new('rm', 'REMESH'); r.mode = 'VOXEL'; r.voxel_size = 0.004; apply(r)
    if hi.name.startswith(WELD):
        wd = lo.modifiers.new('wd', 'WELD'); wd.merge_threshold = 0.0005; apply(wd)
    tris = sum(len(p.vertices)-2 for p in lo.data.polygons); goal = max(60, int(budget*w/tot_w))
    if tris > goal:
        d = lo.modifiers.new('dec', 'DECIMATE'); d.ratio = goal/tris; d.use_collapse_triangulate = True; apply(d)
    # voxel remesh loses weights: copy them back from the original
    if hi.name.startswith(REMESH):
        dt = lo.modifiers.new('dt', 'DATA_TRANSFER'); dt.object = hi; dt.use_vert_data = True
        dt.data_types_verts = {'VGROUP_WEIGHTS'}; dt.vert_mapping = 'NEAREST'
        for vg in hi.vertex_groups: lo.vertex_groups.new(name=vg.name)
        apply(dt)
    # fresh UVs
    for uv in list(lo.data.uv_layers): lo.data.uv_layers.remove(uv)
    lo.data.uv_layers.new(name='UV')
    bm = bmesh.new(); bm.from_mesh(lo.data); bm.to_mesh(lo.data); bm.free()
    bpy.ops.object.select_all(action='DESELECT'); bpy.context.view_layer.objects.active = lo; lo.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=1.15, island_margin=0.01); bpy.ops.object.mode_set(mode='OBJECT')
    # target image + simple material
    img = bpy.data.images.new(lo.name + '_col', tex, tex, alpha=False)
    mat = bpy.data.materials.new(lo.name + '_mat'); mat.use_nodes = True
    nt = mat.node_tree; bsdf = nt.nodes['Principled BSDF']; bsdf.inputs['Roughness'].default_value = 0.9
    node = nt.nodes.new('ShaderNodeTexImage'); node.image = img; nt.links.new(node.outputs[0], bsdf.inputs['Base Color'])
    nt.nodes.active = node
    lo.data.materials.clear(); lo.data.materials.append(mat)
    # bake
    srcs = [hi] + (shag if extra == 'shag' else [])
    for s in srcs: s.select_set(True)
    bpy.context.view_layer.objects.active = lo
    bk.cage_extrusion = 0.02; bk.max_ray_distance = 0.06
    bpy.ops.object.bake(type='DIFFUSE')
    img.filepath_raw = os.path.join(texdir, img.name + '.png'); img.file_format = 'PNG'; img.save()
    nt_ = sum(len(p.vertices)-2 for p in lo.data.polygons); total += nt_
    print(f'BAKED {lo.name:40} {nt_:>6} tris  {tex}px  {time.time()-t0:5.1f}s', flush=True)
print('TOTAL', total)
# keep only the reduced meshes
for o in highs: bpy.data.objects.remove(o)
bpy.ops.file.pack_all(); bpy.ops.outliner.orphans_purge(do_recursive=True)
bpy.ops.wm.save_as_mainfile(filepath=out)
