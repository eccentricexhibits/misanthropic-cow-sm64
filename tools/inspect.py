import bpy, sys, time
glb=sys.argv[-1]
bpy.ops.wm.read_factory_settings(use_empty=True)
t=time.time(); bpy.ops.import_scene.gltf(filepath=glb); print('import s',round(time.time()-t,1))
arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]
print('armature',arm.name,'scale',tuple(arm.scale),'rot',tuple(arm.rotation_euler))
mw=arm.matrix_world
for b in arm.data.bones:
    h=mw@b.head_local; t2=mw@b.tail_local
    print(f'{b.name:18} parent={b.parent.name if b.parent else "-":14} head=({h.x:+.3f},{h.y:+.3f},{h.z:+.3f}) len={b.length:.3f}')
zs=[ (o.matrix_world@v.co).z for o in bpy.data.objects if o.type=='MESH' for v in list(o.data.vertices)[::50]]
print('mesh z range',min(zs),max(zs))
bpy.ops.wm.save_as_mainfile(filepath=sys.argv[-2])
