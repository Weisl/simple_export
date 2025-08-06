from .. import __package__ as base_package


def call_simple_add_exporter_to_collection(context, collection, layout):
    op = layout.operator('simple_export.add_settings_to_collections', icon='COLLECTION_COLOR_01')
    op.collection_name = collection.name

    # Get and set properties from preferences/scene
    prefs = context.preferences.addons[base_package].preferences
    scene = context.scene
    # Collection settings - use scene if overwrite is enabled, else prefs
    collection_settings = scene if scene.overwrite_collection_settings else prefs
    op.collection_prefix = collection_settings.collection_prefix
    op.collection_suffix = collection_settings.collection_suffix
    op.collection_blend_prefix = collection_settings.collection_blend_prefix
    op.collection_color = collection_settings.collection_color
    op.collection_instance_offset = collection_settings.collection_set_location_offset_on_creation
    op.use_root_object = collection_settings.collection_use_root_offset_object
    # Preset settings - use scene if overwrite is enabled, else prefs
    preset_settings = scene if scene.overwrite_collection_settings else prefs
    op.set_preset = preset_settings.set_preset
    op.set_export_path = preset_settings.set_export_path
    # Get preset filepath if auto-set is enabled
    op.preset_filepath = ""
    if scene.set_preset:
        export_format = scene.export_format.lower()
        prop_name = f"simple_export_preset_file_{export_format}"
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
    return op


def call_simple_export_path_ops(context, layout, text='Assign Filepaths', outliner=False,
                                individual_collection=False, collection_name=''):
    op = layout.operator("simple_export.set_export_paths", text=text, icon='FOLDER_REDIRECT')

    op.outliner = outliner
    op.individual_collection = individual_collection
    op.collection_name = collection_name

    # Get and set properties from preferences/scene
    prefs = context.preferences.addons[base_package].preferences
    scene = context.scene
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
    return op


def call_create_export_collection_op(context, icon, layout, text=None):
    if text is None:
        op = layout.operator("simple_export.create_export_collections", icon=icon)
    else:
        op = layout.operator("simple_export.create_export_collections", text=text, icon=icon)

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
    op.collection_blend_prefix = collection_settings.collection_blend_prefix
    op.collection_color = collection_settings.collection_color
    op.collection_instance_offset = collection_settings.collection_set_location_offset_on_creation
    op.use_root_object = collection_settings.collection_use_root_offset_object
    # Preset settings - use scene if overwrite is enabled, else prefs
    preset_settings = scene if scene.overwrite_collection_settings else prefs
    op.set_preset = preset_settings.set_preset
    op.set_export_path = preset_settings.set_export_path
    # Get preset filepath if auto-set is enabled
    op.preset_filepath = ""
    if scene.set_preset:
        export_format = scene.export_format.lower()
        prop_name = f"simple_export_preset_file_{export_format}"
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
    return op
