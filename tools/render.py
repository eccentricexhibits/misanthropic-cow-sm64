import bpy, sys, math, mathutils
blend, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=blend)
for o in list(bpy.data.objects):
    if o.name.startswith('Icosphere'): bpy.data.objects.remove(o)
for o in bpy.data.objects:
    if o.type=='ARMATURE': o.animation_data_clear() if o.animation_data else None; o.data.pose_position='REST'
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=24; sc.cycles.use_denoising=True
sc.render.resolution_x=1600; sc.render.resolution_y=1000; sc.render.film_transparent=False
w=bpy.data.worlds.new('w'); sc.world=w; w.use_nodes=True; w.node_tree.nodes['Background'].inputs[0].default_value=(0.55,0.62,0.72,1); w.node_tree.nodes['Background'].inputs[1].default_value=0.8
sun=bpy.data.objects.new('sun',bpy.data.lights.new('sun','SUN')); sun.data.energy=3; sun.rotation_euler=(math.radians(50),0,math.radians(30)); sc.collection.objects.link(sun)
cam=bpy.data.objects.new('cam',bpy.data.cameras.new('cam')); cam.data.type='ORTHO'; cam.data.ortho_scale=3.2
cam.location=(0.75,-6,0.86); cam.rotation_euler=(math.radians(90),0,0); sc.collection.objects.link(cam); sc.camera=cam
# make a turned copy: duplicate everything rotated for 3/4 view
objs=[o for o in bpy.data.objects if o.type in('MESH','ARMATURE') and o.parent is None]
for o in objs:
    c=o.copy(); sc.collection.objects.link(c); c.location.x+=1.5; c.rotation_euler.z=math.radians(-40)
    for ch in o.children:
        cc=ch.copy(); cc.data=ch.data; sc.collection.objects.link(cc); cc.parent=c
        for m in cc.modifiers:
            if m.type=='ARMATURE': m.object=c
sc.render.filepath=out; bpy.ops.render.render(write_still=True)
