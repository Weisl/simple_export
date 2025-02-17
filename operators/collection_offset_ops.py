import bpy

from ..functions.collection_layer import set_active_layer_Collection
from ..functions.collection_offset import set_collection_offset



class OBJECT_OT_set_collection_offset_cursor(bpy.types.Operator):
    """Set the collection offset to the 3D cursor location."""
    bl_idname = "object.set_collection_offset_cursor"
    bl_label = "Set Collection Center (3D Cursor)"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty(name="Collection Name", default='',
                                              description="Name of the collection to process")

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)

        if not collection:
            self.report({'WARNING'}, "No valid collection found.")
            return {'CANCELLED'}

        set_active_layer_Collection(collection.name)

        # Get the 3D cursor location
        cursor_location = context.scene.cursor.location.copy()
        set_collection_offset(collection, cursor_location)

        self.report({'INFO'}, f"Collection offset set to cursor location: {cursor_location}")
        return {'FINISHED'}



class OBJECT_OT_set_collection_offset_object(bpy.types.Operator):
    """Set the collection offset to the selected object's location."""
    bl_idname = "object.set_collection_offset_object"
    bl_label = "Set Collection Center"
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

        # Set the collection offset to the object's location
        obj_location = obj.location.copy()
        set_collection_offset(collection, obj_location)

        return {'FINISHED'}


classes = (
    OBJECT_OT_set_collection_offset_object,
    OBJECT_OT_set_collection_offset_cursor,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
