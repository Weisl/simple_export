import bpy


class SIMPLEEXPORT_OT_remove_exporters(bpy.types.Operator):
    """Fix the export filename for a collection."""
    bl_idname = "simple_export.remove_exporters"
    bl_label = "Remove all Exporters from Collection"
    bl_description = "Remove all exporters from the specified collection."
    bl_options = {'REGISTER', 'UNDO'}

    # Internal Properties
    collection_name: bpy.props.StringProperty(
        name="Collection Name",
        description="Name of the collection to fix",
        default="",
        options={'HIDDEN'}
    )

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)

        from ..functions.exporter_funcs import remove_all_collection_exporters
        remove_all_collection_exporters(collection)
        self.report({'INFO'}, f"Removed all exporters from collection: {collection.name}")

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
        unregister_class(cls)
