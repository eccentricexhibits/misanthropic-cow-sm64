"""Export a .blend (meshes, rig and animations) to a glTF binary.
Usage: python -I export_glb.py -- <in.blend> <out.glb>"""
import bpy, sys
bpy.ops.wm.open_mainfile(filepath=sys.argv[-2])
bpy.ops.export_scene.gltf(filepath=sys.argv[-1], export_format='GLB', export_animations=True,
                          export_animation_mode='ACTIONS', export_image_format='AUTO')
