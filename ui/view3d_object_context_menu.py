import bpy

from .. import __package__ as base_package


def add_export_collections_to_menu(self, context):
    """Adds the Simple Export create export collections operator to the object context menu."""
    self.layout.separator()
    op = self.layout.operator("simple_export.create_export_collections", icon='COLLECTION_COLOR_01')
    # Set default properties
    op.only_selection = True
    op.collection_naming_overwrite = False
    op.collection_name_new = ""
    op.use_numbering = False
    op.parent_collection_name = context.scene.parent_collection.name if context.scene.parent_collection else ""
    # Get and set properties from preferences/scene
    prefs = context.preferences.addons[base_package].preferences
    scene = context.scene
    
    # Collection settings - use scene if overwrite is enabled, else prefs
    collection_settings = scene if scene.overwrite_collection_settings else prefs
    op.collection_prefix = collection_settings.collection_prefix
    op.collection_suffix = collection_settings.collection_suffix
    op.filename_blend_prefix = collection_settings.collection_blend_prefix
    op.collection_color = collection_settings.collection_color
    op.collection_instance_offset = collection_settings.collection_set_location_offset_on_creation
    op.use_root_object = collection_settings.collection_use_root_offset_object
    
    # Preset and export path settings
    op.set_preset = scene.set_preset
    op.set_export_path = scene.set_export_path
    
    # Get preset filepath if auto-set is enabled
    op.preset_filepath = ""
    if scene.set_preset:
        export_format = scene.export_format.lower()
        prop_name = f"simple_export_preset_file_{export_format}"
        preset_settings = scene if scene.overwrite_preset_settings else prefs
        op.preset_filepath = getattr(preset_settings, prop_name, "")
    
    # Filepath settings - use scene if overwrite is enabled, else prefs
    filepath_settings = scene if scene.overwrite_filepath_settings else prefs
    op.export_folder_mode = filepath_settings.export_folder_mode
    op.folder_path_absolute = filepath_settings.folder_path_absolute
    op.folder_path_relative = filepath_settings.folder_path_relative
    op.folder_path_search = filepath_settings.folder_path_search
    op.folder_path_replace = filepath_settings.folder_path_replace
    
    # Filename settings - use scene if overwrite is enabled, else prefs
    filename_settings = scene if scene.overwrite_filename_settings else prefs
    op.filename_prefix = filename_settings.filename_prefix
    op.filename_suffix = filename_settings.filename_suffix
    op.filename_blend_prefix = filename_settings.filename_blend_prefix


def register():
    bpy.types.VIEW3D_MT_object_context_menu.append(add_export_collections_to_menu)


def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(add_export_collections_to_menu)
