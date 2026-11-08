"""Push outer clothing layers slightly outward so they don't cut into the layers beneath.
Usage: python -I fix_layers.py -- <in.blend> <out.blend>"""
import bpy, sys
src, out = sys.argv[-2], sys.argv[-1]
bpy.ops.wm.open_mainfile(filepath=src)
OFFSETS = {'Briefs': 0.007}
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    for k, d in OFFSETS.items():
        if o.name.startswith(k):
            m = o.modifiers.new('push', 'DISPLACE'); m.strength = d; m.mid_level = 0
            o.modifiers.move(len(o.modifiers) - 1, 0)
            with bpy.context.temp_override(object=o, active_object=o): bpy.ops.object.modifier_apply(modifier='push')
            print('pushed', o.name, d)
bpy.ops.wm.save_as_mainfile(filepath=out)
