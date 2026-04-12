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

    """Base class for export format presets"""
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
        "scene.simple_export_preset_file_gltf",
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
        # Pre-export operations
        "scene.move_by_collection_offset",
        "scene.triangulate_before_export",
        "scene.triangulate_keep_normals",
        "scene.apply_scale_before_export",
        "scene.apply_rotation_before_export",
        "scene.apply_transform_before_export",
        "scene.pre_rotate_objects",
        "scene.pre_rotate_euler",
    ]

    # Directory to store the presets
    preset_subdir = f"{folder_name}"


class SceneExportPreset(BaseExportPreset):
    """Presets for scene export settings"""
    bl_idname = "simple_export.scene_preset"
    bl_label = "Export Format Presets"
    preset_menu = "EXPORT_MT_scene_presets"

    def execute(self, context):
        result = super().execute(context)
        if not self.remove_active:
            preset_path = os.path.join(simple_export_presets_folder(), self.as_filename() + ".py")
            context.scene.simple_export_selected_preset = preset_path
        else:
            if context.scene.simple_export_selected_preset:
                context.scene.simple_export_selected_preset = ""
        return result


class SIMPLE_EXPORT_OT_set_default_preset(bpy.types.Operator):
    """Pin this preset as the default applied when opening a new blend file"""
    bl_idname = "simple_export.set_default_preset"
    bl_label = "Set as Default Export Format Preset"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences
        selected_preset = context.scene.simple_export_selected_preset
        if selected_preset:
            prefs.simple_export_default_preset = selected_preset
            bpy.ops.wm.save_userpref()
            self.report({'INFO'}, f"Default preset set to: {os.path.basename(selected_preset)}")
        else:
            self.report({'WARNING'}, "No preset selected. Apply a preset first.")
        return {'FINISHED'}


class SIMPLE_EXPORT_OT_ApplyPreset(bpy.types.Operator):
    """Apply an export format preset and track it as the currently selected preset"""
    bl_idname = "simple_export.apply_preset"
    bl_label = "Apply Export Format Preset"
    bl_options = {'REGISTER', 'INTERNAL'}

    filepath: bpy.props.StringProperty()
    menu_idname: bpy.props.StringProperty()

    def execute(self, context):
        bpy.ops.script.execute_preset(
            filepath=self.filepath,
            menu_idname=EXPORT_MT_scene_presets.__name__,
        )
        context.scene.simple_export_selected_preset = self.filepath
        return {'FINISHED'}


class EXPORT_MT_scene_presets(Menu):
    bl_label = "Export Format Presets"
    preset_subdir = BaseExportPreset.preset_subdir
    preset_operator = "simple_export.apply_preset"
    draw = Menu.draw_preset


classes = (
    SceneExportPreset,
    SIMPLE_EXPORT_OT_ApplyPreset,
    SIMPLE_EXPORT_OT_set_default_preset,
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
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)


if __name__ == "__main__":
    register()
