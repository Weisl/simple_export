import bpy

from ..functions.outliner_func import get_outliner_collections


class SIMPLEEXPORT_OT_remove_exporters(bpy.types.Operator):
    """Fix the export filename for a collection."""
    bl_idname = "simple_export.remove_exporters"
    bl_label = "Remove all Exporters from Collection"
    bl_description = "Remove all exporters from the specified collection."
    bl_options = {'REGISTER', 'UNDO'}

    # Internal Properties
    outliner: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    collection_name: bpy.props.StringProperty(
        name="Collection Name",
        description="Name of the collection to fix",
        default="",
        options={'HIDDEN'}
    )

    def execute(self, context):
        if self.outliner:
            collection_list = get_outliner_collections(context)
            if not collection_list:
                self.report({'WARNING'}, "No collections selected in the Outliner.")
                return {'CANCELLED'}
        else:
            collection = bpy.data.collections.get(self.collection_name)
            if not collection:
                self.report({'ERROR'}, f"Collection '{self.collection_name}' not found.")
                return {'CANCELLED'}
            collection_list = [collection]

        from ..functions.exporter_funcs import remove_all_collection_exporters
        for collection in collection_list:
            remove_all_collection_exporters(collection)

        if len(collection_list) == 1:
            self.report({'INFO'}, f"Removed all exporters from collection: {collection_list[0].name}")
        else:
            self.report({'INFO'}, f"Removed all exporters from {len(collection_list)} collections.")

        return {'FINISHED'}

classes = (
    SIMPLEEXPORT_OT_remove_exporters,
)


# Register the scene property
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
