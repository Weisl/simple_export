from .. import __package__ as base_package


def set_operator_preset_property(op, scene):
    export_format = scene.export_format.lower()
    prop_name = f"simple_export_preset_file_{export_format}"
    setattr(op, prop_name, getattr(scene, prop_name))


def call_simple_add_exporter_to_collection(context, collection, layout):
    op = layout.operator('simple_export.add_settings_to_collections', icon='COLLECTION_COLOR_01')
    op.collection_name = collection.name

    # Get and set properties from preferences/scene
    prefs = context.preferences.addons[base_package].preferences
    scene = context.scene

    # Collection settings
    collection_settings = scene
    op.collection_prefix = collection_settings.collection_prefix
    op.collection_suffix = collection_settings.collection_suffix
    op.collection_blend_prefix = collection_settings.collection_blend_prefix
    op.collection_color = collection_settings.collection_color
    op.collection_instance_offset = collection_settings.collection_instance_offset
    op.use_root_object = collection_settings.use_root_object

    # Preset settings
    set_operator_preset_property(op, scene)

    # Filepath settings
    filepath_settings = scene
    op.export_folder_mode = filepath_settings.export_folder_mode
    op.folder_path_absolute = filepath_settings.folder_path_absolute
    op.folder_path_relative = filepath_settings.folder_path_relative
    op.folder_path_search = filepath_settings.folder_path_search
    op.folder_path_replace = filepath_settings.folder_path_replace

    # Filename settings
    filename_settings = scene
    op.filename_prefix = filename_settings.filename_prefix
    op.filename_suffix = filename_settings.filename_suffix
    op.filename_blend_prefix = filename_settings.filename_blend_prefix
    return op


def call_simple_export_path_ops(context, layout, text=None, outliner=False,
                                individual_collection=False, collection_name=''):
    if text is None:
        op = layout.operator("simple_export.set_export_paths", icon='FOLDER_REDIRECT')
    else:
        op = layout.operator("simple_export.set_export_paths", text=text, icon='FOLDER_REDIRECT')

    op.outliner = outliner
    op.individual_collection = individual_collection
    op.collection_name = collection_name

    # Get and set properties from preferences/scene
    prefs = context.preferences.addons[base_package].preferences
    scene = context.scene
    # Filepath settings - use scene if overwrite is enabled, else prefs
    filepath_settings = scene
    op.export_folder_mode = filepath_settings.export_folder_mode
    op.folder_path_absolute = filepath_settings.folder_path_absolute
    op.folder_path_relative = filepath_settings.folder_path_relative
    op.folder_path_search = filepath_settings.folder_path_search
    op.folder_path_replace = filepath_settings.folder_path_replace
    # Filename settings - use scene if overwrite is enabled, else prefs
    filename_settings = scene
    op.filename_prefix = filename_settings.filename_prefix
    op.filename_suffix = filename_settings.filename_suffix
    op.filename_blend_prefix = filename_settings.filename_blend_prefix
    return op


def call_assign_preset_op(context, layout, text=None, icon='PRESET_NEW', outliner=False, individual_collection=False,
                          collection_name=''):
    if text is None:
        op = layout.operator("simple_export.assign_presets", icon=icon)
    else:
        op = layout.operator("simple_export.assign_presets", text=text, icon=icon)

    op.outliner = outliner
    op.individual_collection = individual_collection
    op.collection_name = collection_name

    # Get and set properties from preferences/scene
    scene = context.scene

    # Set file format
    op.export_format = scene.export_format

    # Set preset filepath
    set_operator_preset_property(op, scene)


def call_create_export_collection_op(scene, layout, icon='COLLECTION_NEW', text=None):
    if text is None:
        op = layout.operator("simple_export.create_export_collections", icon=icon)
    else:
        op = layout.operator("simple_export.create_export_collections", text=text, icon=icon)

    # Set default properties
    # op.only_selection = True
    op.collection_naming_overwrite = False
    op.collection_name_new = ""
    op.use_numbering = False
    op.parent_collection = scene.parent_collection if scene.parent_collection else ""

    # Get and set properties from preferences/scene
    scene = scene

    # Export Format
    op.export_format = scene.export_format

    # Collection settings
    collection_settings = scene
    op.collection_prefix = collection_settings.collection_prefix
    op.collection_suffix = collection_settings.collection_suffix
    op.collection_blend_prefix = collection_settings.collection_blend_prefix
    op.collection_color = collection_settings.collection_color
    op.collection_instance_offset = collection_settings.collection_instance_offset
    op.use_root_object = collection_settings.use_root_object

    # Preset settings
    set_operator_preset_property(op, scene)

    # Filepath settings
    filepath_settings = scene
    op.export_folder_mode = filepath_settings.export_folder_mode
    op.folder_path_absolute = filepath_settings.folder_path_absolute
    op.folder_path_relative = filepath_settings.folder_path_relative
    op.folder_path_search = filepath_settings.folder_path_search
    op.folder_path_replace = filepath_settings.folder_path_replace
    # Filename settings
    filename_settings = scene
    op.filename_prefix = filename_settings.filename_prefix
    op.filename_suffix = filename_settings.filename_suffix
    op.filename_blend_prefix = filename_settings.filename_blend_prefix
    return op
