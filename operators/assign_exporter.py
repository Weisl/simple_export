import bpy

from .. import __package__ as base_package
from ..functions.create_collection_func import generate_collection_name, setup_collection
from ..functions.outliner_func import get_outliner_collections


class EXPORT_OT_CreateExportCollections(bpy.types.Operator):
    """
    Create a new collection for each selected object and its children, preserving hierarchy.
    """
    bl_idname = "simple_export.create_export_collections"
    bl_label = "Create Export Collections"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        selected_objects = context.selected_objects
        parent_collection = context.scene.parent_collection or context.scene.collection

        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene
        settings_col = scene if scene.overwrite_collection_settings else prefs
        settings_filepath = scene if scene.overwrite_filepath_settings else prefs

        if not selected_objects:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}

        if not isinstance(parent_collection, bpy.types.Collection):
            self.report({'WARNING'}, "No valid parent collection selected. Falling back to the scene collection.")
            parent_collection = context.scene.collection

        # Identify top-level objects (objects without a selected parent)
        top_level_objects = [obj for obj in selected_objects if not obj.parent or obj.parent not in selected_objects]

        for top_object in top_level_objects:
            collection_name = generate_collection_name(context, top_object.name)

            if collection_name in bpy.data.collections:
                self.report({'WARNING'}, f"Collection '{collection_name}' already exists. Skipping.")
                continue

            export_collection = bpy.data.collections.new(collection_name)
            parent_collection.children.link(export_collection)

            # Gather hierarchy of children recursively
            def collect_children(obj):
                return [obj] + [child for child in bpy.data.objects if child.parent == obj and child in selected_objects]

            hierarchy_objects = collect_children(top_object)

            for obj in hierarchy_objects:
                if export_collection not in obj.users_collection:
                    export_collection.objects.link(obj)

                for col in obj.users_collection:
                    if col != export_collection:
                        col.objects.unlink(obj)

            setup_collection(context, export_collection, top_object, settings_col, settings_filepath)

            self.report({'INFO'}, f"Export collection '{export_collection.name}' created successfully for '{top_object.name}'.")

        return {'FINISHED'}


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
    EXPORT_OT_CreateExportCollections,
    EXPORT_OT_AddSettingsToCollections,
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
