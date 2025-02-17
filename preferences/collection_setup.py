import bpy
from bpy.app.handlers import persistent


@persistent
def update_collection_offset(depsgraph):
    """Update collection offsets for collections with an assigned root_object."""
    print("Depsgraph update triggered")

    for collection in bpy.data.collections:
        # Get the assigned offset object
        offset_obj = getattr(collection, "root_object", None)

        if offset_obj and isinstance(offset_obj, bpy.types.Object):
            # Check if instance_offset needs updating
            if collection.instance_offset != offset_obj.location:
                print(f"Updating collection '{collection.name}' offset to: {offset_obj.location}")
                collection.instance_offset = offset_obj.location


def register():
    bpy.types.Collection.root_object = bpy.props.PointerProperty(
        name="Root Object",
        type=bpy.types.Object,
        description="Object to be used for setting the collection offset"
    )

    """add the handler."""
    if update_collection_offset not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(update_collection_offset)
        print("Registered object location tracker")


def unregister():
    del bpy.types.Collection.root_object

    """remove the handler."""
    if update_collection_offset in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_collection_offset)
        print("Unregistered object location tracker")
