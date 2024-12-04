import os

import bpy
from bl_operators.presets import AddPresetBase
from bpy.types import Menu
from bpy.types import Operator

from .. import __package__ as base_package

ADDON_NAME = base_package if base_package else "Simple Export"
folder_name = 'simple_export'


def get_preset_folder_path():
    """
    Ensure the existence of the presets folder for the addon and return its path.

    Returns:
        str: The path to the collider presets directory.
    """
    # Make sure there is a directory for presets
    preset_folder = "simple_export"
    export_preset_directory = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets", preset_folder)
    export_preset_paths = bpy.utils.preset_paths(preset_folder)

    if (export_preset_directory not in export_preset_paths) and (not os.path.exists(export_preset_directory)):
        os.makedirs(export_preset_directory)

    '''
        The preset folder is apparently the operator class name
        >>> type(C.collection.exporters['FBX'].export_properties)
        <class 'bpy.types.EXPORT_SCENE_OT_fbx'>
        
        >>> type(C.collection.exporters['FBX'].export_properties)
        <class 'bpy.types.EXPORT_SCENE_OT_fbx'>
        
        >>> type(C.collection.exporters[2].export_properties)
        <class 'bpy.types.WM_OT_obj_export'>
        
        >>> type(C.collection.exporters[3].export_properties)
        <class 'bpy.types.WM_OT_usd_export'>
        
        >>> type(C.collection.exporters[1].export_properties)
        <class 'bpy.types.WM_OT_alembic_export'>

    '''

    return export_preset_directory


class PRESET_OT_load_preset(Operator):
    """Presets for collider creation"""
    bl_idname = "export.load_export_preset"
    bl_label = "Load Collider Preset"

    filepath: bpy.props.StringProperty(subtype="FILE_PATH")

    def execute(self, context):
        try:
            bpy.ops.script.execute_preset(filepath=self.filepath, menu_idname="EXPORT_MT_export_presets")
            self.report({'INFO'}, "Preset loaded successfully.")
        except: # upgrade preset before trying it
            # print('preset_update')
            # bpy.ops.object.upgrade_simple_collider_presets()
            bpy.ops.script.execute_preset(filepath=self.filepath, menu_idname="EXPORT_MT_export_presets")
            self.report({'INFO'}, "Updated and loaded preset successfully")

        return {'FINISHED'}


############## PRESET ##############################

class EXPORT_MT_export_presets(Menu):
    """Export preset dropdown"""

    bl_label = "Export Presets"
    bl_description = "Specify export preset"
    preset_subdir = "simple_export"
    preset_operator = "export.load_export_preset"
    subclass = 'PresetMenu'
    draw = Menu.draw_preset


class SIMPLE_EXPORT_preset(AddPresetBase, Operator):
    """Presets for collider creation"""
    bl_idname = "simple_export.simple_export_name_preset"
    bl_label = "Collider Naming Presets"
    preset_menu = "OBJECT_MT_simple_export_presets"

    # Common variable used for all preset values
    preset_defines = [

        # f'prefs = bpy.context.preferences.addons["{ADDON_NAME}"].preferences',
        f'op = bpy.context.active_operator'
    ]

    # properties to store in the preset
    preset_values = [
        "op.filepath",
        # "op.use_selection",
        # "op.use_visible",
        # "op.use_active_collection",
        # "op.collection",
        # "op.global_scale",
        # "op.apply_unit_scale",
        # "op.apply_scale_options",
        # "op.use_space_transform",
        # "op.bake_space_transform",
        # "op.object_types",
        # "op.use_mesh_modifiers",
        # "op.use_mesh_modifiers_render",
        # "op.mesh_smooth_type",
        # "op.prioritize_active_color",
        # "op.use_subsurf",
        # "op.use_tspace",
        # "op.use_triangles",
        # "op.use_custom_props",
        # "op.add_leaf_bones",
        # "op.primary_bone_axis",
        # "op.secondary_bone_axis",
        # "op.use_armature_deform_only",
        # "op.armature_nodetype",
        # "op.bake_anim",
        # "op.bake_anim_use_all_bones",
        # "op.bake_anim_use_nla_strips",
        # "op.bake_anim_use_all_actions",
        # "op.bake_anim_force_startend_keying",
        # "op.bake_anim_step",
        # "op.bake_anim_simplify_factor",
        # "op.path_mode",
        # "op.embed_textures",
        # "op.batch_mode",
        # "op.use_batch_own_dir",
        # "op.axis_forward",
        # "op.axis_up",
    ]

    # Directory to store the presets
    preset_subdir = folder_name


classes = (PRESET_OT_load_preset, EXPORT_MT_export_presets, SIMPLE_EXPORT_preset,)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
