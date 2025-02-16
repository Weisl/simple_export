import bpy

from ..functions.collection_offset import set_collection_offset_from_object
from ..functions.collection_layer import set_active_layer_Collection

def update_collection_offset(scene):
    """Update the collection offset when the object is moved."""
    for collection in bpy.data.collections:
        obj = collection.get("offset_object", None)
        if obj:
            if collection.instance_offset != obj.location:
                set_collection_offset_from_object(collection, obj)



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
    bpy.types.Collection.offset_object = bpy.props.PointerProperty(
        name="Offset Object",
        type=bpy.types.Object,
        description="Object to be used for setting the collection offset"
    )

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    if update_collection_offset not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(update_collection_offset)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Collection.offset_object

    if update_collection_offset in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_collection_offset)
