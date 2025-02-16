import bpy

from . import keymap, preferenecs, collection_setup
from ..functions.collection_offset import update_collection_offset

files = [
    preferenecs,
    keymap,
    collection_setup
]


def register():
    for file in files:
        file.register()

    # Update collection offset automatically
    if update_collection_offset not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(update_collection_offset)


def unregister():
    for file in reversed(files):
        file.unregister()

    # Update collection offset automatically
    if update_collection_offset in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_collection_offset)
