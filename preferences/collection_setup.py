import bpy
from bpy.app.handlers import persistent

from ..functions.collection_layer import set_active_layer_Collection
from ..functions.collection_offset import set_collection_offset_from_object


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


class OBJECT_OT_set_collection_offset(bpy.types.Operator):
    """Set the collection offset to the selected object's location."""
    bl_idname = "object.set_collection_offset"
    bl_label = "Set Collection Offset"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty(name="Collection Name", default='',
                                              description="Name of the collection to process")

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)

        if not collection:
            self.report({'WARNING'}, "No valid collection found.")
            return {'CANCELLED'}

        set_active_layer_Collection(collection.name)
        obj = context.object

        if not obj:
            self.report({'WARNING'}, "No object selected")
            return {'CANCELLED'}

        # Set the collection offset
        set_collection_offset_from_object(collection, obj)

        return {'FINISHED'}


classes = (
    OBJECT_OT_set_collection_offset,
)


def register():
    bpy.types.Collection.root_object = bpy.props.PointerProperty(
        name="Root Object",
        type=bpy.types.Object,
        description="Object to be used for setting the collection offset"
    )

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    """add the handler."""
    if update_collection_offset not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(update_collection_offset)
        print("Registered object location tracker")


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Collection.root_object

    """remove the handler."""
    if update_collection_offset in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_collection_offset)
        print("Unregistered object location tracker")
