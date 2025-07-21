from . import assign_exporter, export_ops, filepath_ops, preset_ops, ui_ops, create_exporter, collection_offset_ops

files = [
    assign_exporter,
    export_ops,
    filepath_ops,
    preset_ops,
    ui_ops,
    create_exporter,
    collection_offset_ops,
]

# Register scene properties here so they're only registered once
import bpy

Scene = bpy.types.Scene


def register_scene_properties():
    if not hasattr(Scene, 'parent_collection'):
        Scene.parent_collection = bpy.props.PointerProperty(
            name="Parent Collection",
            description="Choose the parent collection to link the new collection to",
            type=bpy.types.Collection
        )
    if not hasattr(Scene, 'set_filepath_on_creation'):
        Scene.set_filepath_on_creation = bpy.props.BoolProperty(
            name="Set Filepath",
            description="Set filepath based on blend file location",
        )


def unregister_scene_properties():
    if hasattr(Scene, 'parent_collection'):
        del Scene.parent_collection
    if hasattr(Scene, 'set_filepath_on_creation'):
        del Scene.set_filepath_on_creation


def register():
    register_scene_properties()
    for file in files:
        file.register()


def unregister():
    for file in reversed(files):
        file.unregister()
    unregister_scene_properties()
