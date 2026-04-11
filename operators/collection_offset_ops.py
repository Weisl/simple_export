import bpy

from ..functions.collection_layer import set_active_layer_Collection
from ..functions.collection_offset import set_collection_offset


class OBJECT_OT_create_root_empty(bpy.types.Operator):
    """Create an EMPTY object, parent the selected objects to it, and assign it as the collection's root object."""
    bl_idname = "object.create_root_empty"
    bl_label = "Create Root Empty"
    bl_description = (
        "Create an EMPTY object at the collection offset, "
        "parent selected objects to it, and assign it as the root object"
    )
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty(
        name="Collection Name",
        default='',
        description="Name of the collection to assign the root empty to",
        options={'HIDDEN'},
    )

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if not collection:
            self.report({'WARNING'}, "No valid collection found.")
            return {'CANCELLED'}

        # Place the empty at the collection's current instance_offset
        empty_location = collection.instance_offset.copy()

        # Create the EMPTY object
        empty = bpy.data.objects.new(name=collection.name + "_root", object_data=None)
        empty.empty_display_type = 'PLAIN_AXES'
        empty.location = empty_location

        # Link to the collection
        collection.objects.link(empty)

        # Parent selected top-level objects to the empty, preserving world transforms
        for obj in list(context.selected_objects):
            if obj == empty or obj.parent is not None:
                continue
            world_matrix = obj.matrix_world.copy()
            obj.parent = empty
            # Restore world position: matrix_parent_inverse cancels out the parent transform
            obj.matrix_parent_inverse = empty.matrix_world.inverted()
            obj.matrix_world = world_matrix

        # Make the empty the active object
        context.view_layer.objects.active = empty

        # Assign as root object for the collection
        collection.use_root_object = True
        collection.root_object = empty

        self.report({'INFO'}, f"Created root empty '{empty.name}' for collection '{collection.name}'")
        return {'FINISHED'}


class OBJECT_OT_set_collection_offset_cursor(bpy.types.Operator):
    """Set the collection offset to the 3D cursor location."""
    bl_idname = "object.set_collection_offset_cursor"
    bl_label = "Set Collection Center (3D Cursor)"
    bl_description = "Set Collection Center (3D Cursor)"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}


    # Hidden property for the collection name
    collection_name: bpy.props.StringProperty(name="Collection Name", default='',
                                              description="Name of the collection to process", options={'HIDDEN'}, )

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
    bl_description = "Set Collection Center to the active object's location"
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

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
    OBJECT_OT_create_root_empty,
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
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
