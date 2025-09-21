import bpy
import os
from bl_operators.presets import AddPresetBase
from bpy.types import Menu
from bpy.types import Operator

from .. import __package__ as base_package

ADDON_NAME = base_package if base_package else "simple_export"
folder_name = 'simple_export'


def simple_export_presets_folder():
    """
    Ensure the existence of the presets folder for the addon and return its path.

    Returns:
        str: The path to the collider presets directory.
    """
    # Make sure there is a directory for presets
    simple_export_presets = folder_name
    simple_export_preset_directory = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets", simple_export_presets)
    simple_export_preset_paths = bpy.utils.preset_paths(simple_export_presets)

    if (simple_export_preset_directory not in simple_export_preset_paths) and (
            not os.path.exists(simple_export_preset_directory)):
        os.makedirs(simple_export_preset_directory)

    return simple_export_preset_directory


class BaseExportPreset(AddPresetBase, Operator):
    # Define prop for the scene context
    preset_defines = [
        f"scene = bpy.context.scene"
    ]

    """Base class for export presets"""
    # Common properties for all preset types
    preset_values = [
        "scene.export_format",
        "scene.export_folder_mode",
        "scene.folder_path_absolute",
        "scene.folder_path_relative",
        "scene.folder_path_search",
        "scene.folder_path_replace",
        "scene.filename_prefix",
        "scene.filename_suffix",
        "scene.filename_blend_prefix",
        "scene.set_export_path",
        "scene.simple_export_preset_file_fbx",
        "scene.simple_export_preset_file_obj",
        "scene.simple_export_preset_file_gltf_binary",
        "scene.simple_export_preset_file_gltf_separate",
        "scene.simple_export_preset_file_usd",
        "scene.simple_export_preset_file_abc",
        "scene.simple_export_preset_file_ply",
        "scene.simple_export_preset_file_stl",
        "scene.assign_preset",
        "scene.collection_prefix",
        "scene.collection_suffix",
        "scene.collection_blend_prefix",
        "scene.use_root_object",
        "scene.collection_instance_offset",
        "scene.collection_color",
        "scene.use_root_object",
        "scene.collection_instance_offset",
        "scene.collection_color",
        "scene.parent_collection",
    ]

    # Directory to store the presets
    preset_subdir = f"{folder_name}"


class SceneExportPreset(BaseExportPreset):
    """Presets for scene export settings"""
    bl_idname = "simple_export.scene_preset"
    bl_label = "Export Presets"
    preset_menu = "EXPORT_MT_scene_presets"


class EXPORT_MT_scene_presets(Menu):
    bl_label = "Export Presets"
    preset_subdir = BaseExportPreset.preset_subdir
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


classes = (
    SceneExportPreset,
    EXPORT_MT_scene_presets,
)


# Register and Unregister
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)


if __name__ == "__main__":
    register()
