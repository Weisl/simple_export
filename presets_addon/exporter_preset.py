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

    bl_label = "Exporter"
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
    ]

    # properties to store in the preset
    preset_values = [
        "prefs.naming_position",
        "prefs.replace_name",
        "prefs.obj_basename",
        "prefs.separator",
        "prefs.collision_string_prefix",
        "prefs.collision_string_suffix",
        "prefs.collision_digits",
        "prefs.box_shape",
        "prefs.sphere_shape",
        "prefs.capsule_shape",
        "prefs.convex_shape",
        "prefs.mesh_shape",
        "prefs.rigid_body_naming_position",
        "prefs.rigid_body_extension",
        "prefs.rigid_body_separator",
        "prefs.collider_groups_enabled",
        "prefs.user_group_01",
        "prefs.user_group_02",
        "prefs.user_group_03",
        "prefs.user_group_01_name",
        "prefs.user_group_02_name",
        "prefs.user_group_03_name",
        "prefs.use_physics_material",
        "prefs.material_naming_position",
        "prefs.physics_material_separator",
        "prefs.use_random_color",
        "prefs.physics_material_su_prefix",
        "prefs.physics_material_name",
        "prefs.physics_material_filter",
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
