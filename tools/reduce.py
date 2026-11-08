import bpy, sys, re
out=sys.argv[-1]; target_total=int(sys.argv[-2])
bpy.ops.wm.open_mainfile(filepath=sys.argv[-3])
for o in list(bpy.data.objects):
    if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
# budget weights (share of total) by mesh name prefix; strands removed for now
W={'Suit_torso':25,'Mask_scanned_face':12,'Slipper_L':4,'Slipper_R':4,'Briefs':4,'Glove_L_palm':3,'Glove_R_palm':3,
   'Glove_L_toe':1,'Glove_R_toe':1,'Leggings_L':4,'Leggings_R':4,'Leggings_seat':2,'Udder_L':3,'Udder_R':3,
   'Suit_sleeve_L':3,'Suit_sleeve_R':3,'Hood':4,'Horn':1.2,'Tail_gold':1.5,'Mask_lower_jaw':1.5,'Tail_plug_body':0.8,
   'Mask_horn_tube':0.7,'Tail_lamp_cord':0.6,'Tail_plug_brass':0.4,'Suit_black_shag':0}
def weight(n):
    for k,v in W.items():
        if n.startswith(k): return v
    print('NO WEIGHT',n); return 1
meshes=[o for o in bpy.data.objects if o.type=='MESH']
tot_w=sum(weight(o.name) for o in meshes)
total=0
for o in meshes:
    w=weight(o.name)
    if w==0: bpy.data.objects.remove(o); continue
    if o.data.shape_keys:
        o.shape_key_clear()
    tris=sum(len(p.vertices)-2 for p in o.data.polygons)
    goal=max(60,int(target_total*w/tot_w))
    if tris>goal:
        bpy.context.view_layer.objects.active=o
        m=o.modifiers.new('dec','DECIMATE'); m.decimate_type='COLLAPSE'; m.ratio=goal/tris; m.use_collapse_triangulate=True
        # apply before armature modifier
        while o.modifiers[0].name!='dec': bpy.ops.object.modifier_move_up(modifier='dec')
        with bpy.context.temp_override(object=o): bpy.ops.object.modifier_apply(modifier='dec')
    nt=sum(len(p.vertices)-2 for p in o.data.polygons); total+=nt
    print(f'{o.name:40} {tris:>7} -> {nt:>6}')
print('TOTAL',total)
for img in bpy.data.images:
    if img.size[0]>512: img.scale(512,512*img.size[1]//img.size[0])
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=out)
