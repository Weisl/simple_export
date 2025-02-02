import bpy

from .. import __package__ as base_package
from ..functions.create_collection_func import generate_collection_name, setup_collection
from ..functions.outliner_func import get_outliner_collections


class EXPORT_OT_CreateExportCollection(bpy.types.Operator):
    """
    Create a new collection for the active object and its children.
    """
    bl_idname = "simple_export.create_export_collection"
    bl_label = "Create Export Collection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active_object = context.active_object
        parent_collection = context.scene.parent_collection or context.scene.collection

        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene
        settings_col = scene if scene.overwrite_collection_settings else prefs
        settings_filepath = scene if scene.overwrite_filepath_settings else prefs

        if not active_object:
            self.report({'WARNING'}, "No active object selected.")
            return {'CANCELLED'}

        if not isinstance(parent_collection, bpy.types.Collection):
            self.report({'WARNING'}, "No valid parent collection selected. Falling back to the scene collection.")
            parent_collection = context.scene.collection

        collection_name = generate_collection_name(context, active_object.name)

        if collection_name in bpy.data.collections:
            self.report({'WARNING'}, "Collection already exists")
            return {'CANCELLED'}

        export_collection = bpy.data.collections.new(collection_name)
        parent_collection.children.link(export_collection)

        collection_objects = [active_object] + [obj for obj in bpy.data.objects if obj.parent == active_object]
        for ob in collection_objects:
            if export_collection not in ob.users_collection:
                export_collection.objects.link(ob)

            for col in ob.users_collection:
                if col != export_collection:
                    col.objects.unlink(ob)

        setup_collection(context, export_collection, active_object, settings_col, settings_filepath)

        self.report({'INFO'}, f"Export collection '{export_collection.name}' created successfully.")
        return {'FINISHED'}


class EXPORT_OT_AddSettingsToCollection(bpy.types.Operator):
    """
    Add export settings to an existing collection.
    """
    bl_idname = "simple_export.add_settings_to_collection"
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
    EXPORT_OT_CreateExportCollection,
    EXPORT_OT_AddSettingsToCollection,
)


# Register the scene property
def register():
    from bpy.utils import register_class
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
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    Scene = bpy.types.Scene

    for cls in reversed(classes):
        unregister_class(cls)

    del Scene.parent_collection
    del Scene.set_filepath_on_creation
