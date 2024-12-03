import bpy


def set_collection_offset_from_object(collection, obj):
    """Set the collection offset to the object's location."""
    if collection and obj:
        collection.instance_offset = obj.location


def update_collection_offset(scene):
    """Update the collection offset when the object is moved."""
    for collection in bpy.data.collections:
        obj = collection.get("offset_object", None)
        if obj:
            if collection.instance_offset != obj.location:
                set_collection_offset_from_object(collection, obj)

def register():
    if update_collection_offset not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(update_collection_offset)

def unregister():
    if update_collection_offset in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_collection_offset)