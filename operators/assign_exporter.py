import bpy

from .. import __package__ as base_package
from ..functions.create_collection_func import setup_collection
from ..functions.outliner_func import get_outliner_collections
from .shared_properties import SharedPathProperties, SharedFilenameProperties, draw_operator_filepath_settings

class EXPORT_OT_AddSettingsToCollections(SharedPathProperties, SharedFilenameProperties, bpy.types.Operator):
    """
    Add export settings to an existing collection.
    """
    bl_idname = "simple_export.add_settings_to_collections"
    bl_label = "Add Exporter to Collection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        success = 0
        collection_list = get_outliner_collections(context)
        last_collection_name = ''
        for i, collection in enumerate(collection_list):
            active_object = context.active_object
            if not collection:
                continue
            last_collection_name = collection.name
            # Pass operator properties directly
            setup_collection(
                context,
                collection,
                active_object,
                self,  # collection settings
                self,  # filepath settings
                self   # filename settings
            )
            success += 1

        # Cancel for No success
        if success == 0:
            self.report({'WARNING'}, "No active collection selected.")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Settings added to collection '{last_collection_name}' successfully.")
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        box = layout.box()
        box.label(text="File Path Settings")
        draw_operator_filepath_settings(box, self)
        box = layout.box()
        box.label(text="File Name Settings")
        box.prop(self, "filename_file_name_prefix")
        box.prop(self, "filename_custom_prefix")
        box.prop(self, "filename_custom_suffix")

classes = (
    EXPORT_OT_AddSettingsToCollections,
)

def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
