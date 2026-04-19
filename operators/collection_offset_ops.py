import bpy

from ..functions.collection_layer import set_active_layer_Collection
from ..functions.collection_offset import set_collection_offset


def create_root_empty_for_collection(
    collection, location,
    objects_to_parent=None,
    display_type='PLAIN_AXES',
    display_size=1.0,
    suffix="_root",
):
    """Create an empty, link it to *collection*, optionally parent objects to it,
    and assign it as the collection's root object.

    Args:
        collection: The Blender collection to link the empty into and set as root.
        location: World-space location (Vector or 3-tuple) for the empty.
        objects_to_parent: Optional iterable of objects whose top-level items (no parent)
                           should be parented to the empty, preserving world transforms.
        display_type: Blender empty_display_type identifier (default 'PLAIN_AXES').
        display_size: empty_display_size in Blender units (default 1.0).
    Returns:
        The newly created EMPTY object.
    """
    empty = bpy.data.objects.new(name=collection.name + suffix, object_data=None)
    empty.empty_display_type = display_type
    empty.empty_display_size = display_size
    empty.location = location

    collection.objects.link(empty)

    # Parent top-level objects to the empty, preserving world transforms.
    # Newly created objects haven't been depsgraph-evaluated, so empty.matrix_world
    # is unreliable. Instead, build the empty's world matrix from its location
    # directly and compute matrix_local = empty_world_inv @ obj_world.
    if objects_to_parent:
        from mathutils import Matrix
        empty_world_matrix = Matrix.Translation(location)
        collection_objects_set = set(collection.objects)
        for obj in objects_to_parent:
            if obj == empty or (obj.parent is not None and obj.parent in collection_objects_set):
                continue
            world_matrix = obj.matrix_world.copy()
            obj.parent = empty
            obj.matrix_parent_inverse.identity()
            obj.matrix_local = empty_world_matrix.inverted() @ world_matrix

    collection.use_root_object = True
    collection.root_object = empty
    return empty


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
