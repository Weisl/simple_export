import bpy

from .. import __package__ as base_package
from ..functions.create_collection_func import setup_collection
from ..functions.outliner_func import get_outliner_collections


class EXPORT_OT_AddSettingsToCollections(bpy.types.Operator):
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

            prefs = context.preferences.addons[base_package].preferences
            scene = context.scene
            settings_col = scene if scene.overwrite_collection_settings else prefs
            settings_filepath = scene if scene.overwrite_filepath_settings else prefs

            if not collection:
                continue
            last_collection_name = collection.name
            setup_collection(context, collection, active_object, settings_col, settings_filepath)
            success += 1

        # Cancel for No success
        if success == 0:
            self.report({'WARNING'}, "No active collection selected.")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Settings added to collection '{last_collection_name}' successfully.")
        return {'FINISHED'}


classes = (
    EXPORT_OT_AddSettingsToCollections,
)


# Register the scene property
def register():
    Scene = bpy.types.Scene
    Scene.parent_collection = bpy.props.PointerProperty(
        name="Parent Collection",
        description="Choose the parent collection to link the new collection to",
        type=bpy.types.Collection
    )
    Scene.set_filepath_on_creation = bpy.props.BoolProperty(
        name="Set Filepath",
        description="Set filepath based on blend file location",
    )
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    Scene = bpy.types.Scene

    for cls in reversed(classes):
        unregister_class(cls)

    del Scene.parent_collection
    del Scene.set_filepath_on_creation
