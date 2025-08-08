import bpy
from bl_operators.presets import AddPresetBase
from bpy.types import Menu
from bpy.types import Operator

from .. import __package__ as base_package

ADDON_NAME = base_package if base_package else "simple_export"
folder_name = 'simple_export'


############## PRESET ##############################
class EXPORT_MT_addon_presets(Menu):
    """Collider preset dropdown"""

    bl_label = "WIP - DONT USE"
    bl_description = "Specify exporter settings"
    preset_subdir = "simple_export"
    preset_operator = "simple_export.load_exporter_preset"
    subclass = 'PresetMenu'
    draw = Menu.draw_preset


class PRESET_OT_load_preset(Operator):
    """Presets for simple export"""
    bl_idname = "simple_export.load_exporter_preset"
    bl_label = "Load Exporter Preset"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        try:
            bpy.ops.script.execute_preset(filepath=self.filepath, menu_idname="EXPORT_MT_addon_presets")
            self.report({'INFO'}, "Preset loaded successfully.")
        except:
            print('preset_update')
            bpy.ops.object.upgrade_simple_collider_presets()
            bpy.ops.script.execute_preset(filepath=self.filepath, menu_idname="EXPORT_MT_addon_presets")
            self.report({'INFO'}, "Updated and loaded preset successfully")

        return {'FINISHED'}


class SIMPLE_EXPORT_preset(AddPresetBase, Operator):
    """Presets for collider creation"""
    bl_idname = "simple_export.collision_name_preset"
    bl_label = "Simple Export Naming Presets"
    preset_menu = "EXPORT_MT_addon_presets"

    # Common variable used for all preset values
    preset_defines = [

        f'prefs = bpy.context.preferences.addons["{ADDON_NAME}"].preferences',
        f'scene = bpy.context.scene',
    ]

    # properties to store in the preset
    preset_values = [
        "scene.export_format",
        "scene.simple_export_preset_file_fbx",
        "scene.simple_export_preset_file_obj",
        "scene.simple_export_preset_file_gltf",
        "scene.simple_export_preset_file_usd",
        "scene.simple_export_preset_file_abc",
        "scene.simple_export_preset_file_ply",
        "scene.simple_export_preset_file_stl",
        "scene.set_preset",
        "scene.collection_prefix",
        "scene.collection_suffix",
        "scene.collection_blend_prefix",
        "scene.use_root_object",
        "scene.collection_instance_offset",
        "scene.collection_color",
    ]

    # Directory to store the presets_export
    preset_subdir = folder_name

classes = (
    SIMPLE_EXPORT_preset,
    EXPORT_MT_addon_presets,
    PRESET_OT_load_preset

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
