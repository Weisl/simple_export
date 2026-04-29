from . import assign_exporter_ops, export_ops, set_filepath_ops, assign_preset_ops, ui_ops, \
    create_exporter_collection_ops, collection_offset_ops, remove_exporters_ops, fix_filename, \
    fix_multiple_exporters, relative_folder_picker, reload_addon, convert_filepath_ops, \
    create_instance_collection_ops, asset_metadata_ops
from .version_check import start_version_check

files = [
    assign_exporter_ops,
    export_ops,
    set_filepath_ops,
    assign_preset_ops,
    ui_ops,
    create_exporter_collection_ops,
    collection_offset_ops,
    remove_exporters_ops,
    fix_filename,
    fix_multiple_exporters,
    relative_folder_picker,
    reload_addon,
    convert_filepath_ops,
    create_instance_collection_ops,
    asset_metadata_ops,
]

# Register scene properties here so they're only registered once
import bpy

Scene = bpy.types.Scene


def register_scene_properties():
    if not hasattr(Scene, 'parent_collection'):
        Scene.parent_collection = bpy.props.StringProperty(
            name="Parent Collection",
            description="Choose the parent collection to link the new collection to",
            default=''
        )
    if not hasattr(Scene, 'set_filepath_on_creation'):
        Scene.set_filepath_on_creation = bpy.props.BoolProperty(
            name="Set Filepath",
            description="Set filepath based on blend file location",
            default=True
        )
    if not hasattr(Scene, 'asset_meta_author'):
        Scene.asset_meta_author = bpy.props.StringProperty(name="Author", default="")
    if not hasattr(Scene, 'asset_meta_license'):
        Scene.asset_meta_license = bpy.props.StringProperty(name="License", default="")
    if not hasattr(Scene, 'asset_meta_copyright'):
        Scene.asset_meta_copyright = bpy.props.StringProperty(name="Copyright", default="")
    if not hasattr(Scene, 'asset_meta_description'):
        Scene.asset_meta_description = bpy.props.StringProperty(name="Description", default="")


def unregister_scene_properties():
    if hasattr(Scene, 'parent_collection'):
        del Scene.parent_collection
    if hasattr(Scene, 'set_filepath_on_creation'):
        del Scene.set_filepath_on_creation
    for prop in ('asset_meta_author', 'asset_meta_license', 'asset_meta_copyright', 'asset_meta_description'):
        if hasattr(Scene, prop):
            delattr(Scene, prop)


def register():
    register_scene_properties()
    for file in files:
        file.register()

    start_version_check()


def unregister():
    for file in reversed(files):
        file.unregister()
    unregister_scene_properties()
