import os

import bpy

from .operators import generate_export_path, assign_exporter_path
from .operators import set_active_layer_Collection
from .panels import EXPORT_FORMATS
from .presets import assign_preset


def generate_collection_name(context, obj_name):
    prefs = bpy.context.preferences.addons[__package__].preferences
    wm = context.window_manager
    settings_col = wm if wm.overwrite_collection_settings else prefs

    collection_name = obj_name
    if getattr(settings_col, 'use_blend_file_name_as_prefix'):
        blend_file_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        if not collection_name.startswith(blend_file_name):
            collection_name = blend_file_name + "_" + collection_name

    prefix = getattr(settings_col, 'custom_prefix')
    suffix = getattr(settings_col, 'custom_suffix')

    if prefix and not collection_name.startswith(prefix):
        collection_name = prefix + "_" + collection_name

    if suffix and not collection_name.endswith(suffix):
        collection_name = collection_name + "_" + suffix

    return collection_name


def setup_collection(context, collection, active_object, settings_col, settings_filepath):
    wm = context.window_manager
    prefs = bpy.context.preferences.addons[__package__].preferences

    # Set collection properties
    collection['simple_export_selected'] = True
    color_tag = getattr(settings_col, 'collection_color')
    collection.color_tag = color_tag

    if getattr(settings_col, 'set_location_offset_on_creation'):
        collection.instance_offset = active_object.location

    # Assign exporter
    set_active_layer_Collection(collection.name)

    export_data = EXPORT_FORMATS.get(wm.export_format)

    def get_all_exporters():
        return list(collection.exporters)

    exporters_before = get_all_exporters()
    bpy.ops.collection.exporter_add(name=export_data["op_name"])
    exporters_after = get_all_exporters()

    exporter = list(set(exporters_after) - set(exporters_before))[0]

    if getattr(settings_col, 'auto_set_preset'):
        # Construct the property name dynamically
        export_format = wm.export_format.lower()
        prop_name = f"simple_export_preset_file_{export_format}"

        # Get preset path
        preset_settings = wm if wm.overwrite_preset_settings else prefs
        preset_path = getattr(preset_settings, prop_name, None)

        assign_preset(exporter, preset_path)

    if getattr(settings_col, 'auto_set_filepath'):
        blend_dir = os.path.dirname(bpy.data.filepath)
        search_path = getattr(settings_filepath, 'search_path')
        replacement_path = getattr(settings_filepath, 'replacement_path')

        export_format = wm.export_format
        export_path = generate_export_path(collection.name, export_format, blend_dir, search_path, replacement_path)
        assign_exporter_path(exporter, export_path)


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

        prefs = bpy.context.preferences.addons[__package__].preferences
        wm = context.window_manager
        settings_col = wm if wm.overwrite_collection_settings else prefs
        settings_filepath = wm if wm.overwrite_filepath_settings else prefs

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
        active_collection = context.collection
        active_object = context.active_object

        prefs = bpy.context.preferences.addons[__package__].preferences
        wm = context.window_manager
        settings_col = wm if wm.overwrite_collection_settings else prefs
        settings_filepath = wm if wm.overwrite_filepath_settings else prefs

        if not active_collection:
            self.report({'WARNING'}, "No active collection selected.")
            return {'CANCELLED'}

        setup_collection(context, active_collection, active_object, settings_col, settings_filepath)

        self.report({'INFO'}, f"Settings added to collection '{active_collection.name}' successfully.")
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
