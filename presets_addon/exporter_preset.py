import os

import bpy
from bl_operators.presets import AddPresetBase
from bpy.props import StringProperty, EnumProperty
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
    collider_preset_directory = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets", simple_export_presets)
    collider_preset_paths = bpy.utils.preset_paths(simple_export_presets)

    if (collider_preset_directory not in collider_preset_paths) and (not os.path.exists(collider_preset_directory)):
        os.makedirs(collider_preset_directory)

    return collider_preset_directory


############## PRESET ##############################


class SIMPLEEXPORT_OT_load_preset(Operator):
    """Load and apply presets for simple export"""
    bl_idname = "simple_export.load_exporter_preset"
    bl_label = "Load Exporter Preset"

    # Define an enum property for context type
    context_type: EnumProperty(
        name="Context Type",
        description="Context to apply the preset to",
        items=[
            ('SCENE', "Scene", "Apply preset to the scene context"),
            ('PREFS', "Preferences", "Apply preset to the preferences context"),
            ('OP', "Operator", "Apply preset to the operator context")
        ],
        default='SCENE'
    )

    filepath: StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        try:
            # Load the preset using Blender's built-in functionality
            bpy.ops.script.execute_preset(filepath=self.filepath, menu_idname="EXPORT_MT_addon_presets")
            self.report({'INFO'}, "Preset loaded successfully.")
        except Exception as e:
            print(f"Error loading preset: {e}")
            # # Handle preset upgrade if necessary
            # if hasattr(bpy.ops.object, "upgrade_simple_collider_presets"):
            #     bpy.ops.object.upgrade_simple_collider_presets()
            # bpy.ops.script.execute_preset(filepath=self.filepath, menu_idname="EXPORT_MT_addon_presets")
            # self.report({'INFO'}, "Updated and loaded preset successfully")

        # Apply the preset values to the specified context
        self.apply_preset_to_context(context)

        return {'FINISHED'}

    def apply_preset_to_context(self, context):
        # Determine the context based on the enum property
        if self.context_type == 'PREFS':
            target = context.preferences.addons.get(ADDON_NAME).preferences
        elif self.context_type == 'OP':
            target = self
        else:  # Default to scene
            target = context.scene

        # Assuming the preset values are loaded into the current context.scene
        source = context.scene

        # Copy the preset values from the source to the target
        for prop_name in BaseExportPreset.preset_values:
            if hasattr(source, prop_name) and hasattr(target, prop_name):
                setattr(target, prop_name, getattr(source, prop_name))


class BaseExportPreset(AddPresetBase, Operator):


    """Base class for export presets"""
    # Common properties for all preset types
    preset_values = [
        "prop.export_format",
        "prop.simple_export_preset_file_fbx",
        "prop.simple_export_preset_file_obj",
        "prop.simple_export_preset_file_gltf",
        "prop.simple_export_preset_file_usd",
        "prop.simple_export_preset_file_abc",
        "prop.simple_export_preset_file_ply",
        "prop.simple_export_preset_file_stl",
        "prop.set_preset",
        "prop.collection_prefix",
        "prop.collection_suffix",
        "prop.collection_blend_prefix",
        "prop.use_root_object",
        "prop.collection_instance_offset",
        "prop.collection_color",
    ]

    # Directory to store the presets
    preset_subdir = "export_presets"


class SceneExportPreset(BaseExportPreset):
    """Presets for scene export settings"""
    bl_idname = "simple_export.scene_preset"
    bl_label = "Scene Export Presets"
    preset_menu = "EXPORT_MT_scene_presets"

    # Define prop for the scene context
    preset_defines = [
        f"prop = bpy.context.scene"
    ]


class PrefsExportPreset(BaseExportPreset):
    """Presets for preferences export settings"""
    bl_idname = "simple_export.prefs_preset"
    bl_label = "Preferences Export Presets"
    preset_menu = "EXPORT_MT_prefs_presets"

    # Define prop for the preferences context
    preset_defines = [
        f'prop = bpy.context.preferences.addons["{ADDON_NAME}"].preferences',
    ]


class OperatorExportPreset(BaseExportPreset):
    """Presets for operator export settings"""
    bl_idname = "simple_export.operator_preset"
    bl_label = "Operator Export Presets"
    preset_menu = "EXPORT_MT_operator_presets"

    # Define prop for the operator context
    preset_defines = [
        f"prop = self"
    ]


class EXPORT_MT_scene_presets(Menu):
    bl_label = "Scene Export Presets"
    preset_subdir = BaseExportPreset.preset_subdir
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


class EXPORT_MT_prefs_presets(Menu):
    bl_label = "Preferences Export Presets"
    preset_subdir = BaseExportPreset.preset_subdir
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


class EXPORT_MT_operator_presets(Menu):
    bl_label = "Operator Export Presets"
    preset_subdir = BaseExportPreset.preset_subdir
    preset_operator = "script.execute_preset"
    draw = Menu.draw_preset


classes = (
    SceneExportPreset,
    PrefsExportPreset,
    OperatorExportPreset,
    EXPORT_MT_scene_presets,
    EXPORT_MT_prefs_presets,
    EXPORT_MT_operator_presets,
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
