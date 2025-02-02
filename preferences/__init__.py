import bpy

from . import keymap, preferenecs
from ..functions.collection_offset import update_collection_offset

files = [
    keymap,
    preferenecs,
]


def register():
    bpy.types.WindowManager.export_data_info = bpy.props.StringProperty(default="[]")
    bpy.types.WindowManager.assign_filepath_result_info = bpy.props.StringProperty(default="[]")

    for file in files:
        file.register()

    # Update collection offset automatically
    if update_collection_offset not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(update_collection_offset)


def unregister():
    del bpy.types.WindowManager.export_data_info
    del bpy.types.WindowManager.assign_filepath_result_info

    for file in reversed(files):
        file.unregister()

    # Update collection offset automatically
    if update_collection_offset in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_collection_offset)
