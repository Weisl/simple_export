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


class SIMPLE_EXPORT_OT_SavePresetFromPreferences(bpy.types.Operator):
    """Save the current preference defaults as a new addon preset"""
    bl_idname = "simple_export.save_preset_from_preferences"
    bl_label = "Save as New Preset"
    bl_options = {'REGISTER', 'INTERNAL'}

    name: bpy.props.StringProperty(
        name="Preset Name",
        description="Name for the new preset",
        default="My Preset",
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "name")

    def execute(self, context):
        name = self.name.strip()
        if not name:
            self.report({'WARNING'}, "Preset name cannot be empty.")
            return {'CANCELLED'}

        prefs = context.preferences.addons[base_package].preferences
        preset_dir = simple_export_presets_folder()
        filename = name.replace(" ", "_") + ".py"
        filepath = os.path.join(preset_dir, filename)

        prop_names = [
            "export_format",
            "export_folder_mode",
            "folder_path_absolute",
            "folder_path_relative",
            "folder_path_search",
            "folder_path_replace",
            "filename_prefix",
            "filename_suffix",
            "filename_blend_prefix",
            "set_export_path",
            "simple_export_preset_file_fbx",
            "simple_export_preset_file_obj",
            "simple_export_preset_file_gltf",
            "simple_export_preset_file_usd",
            "simple_export_preset_file_abc",
            "simple_export_preset_file_ply",
            "simple_export_preset_file_stl",
            "assign_preset",
            "collection_prefix",
            "collection_suffix",
            "collection_blend_prefix",
            "use_root_object",
            "collection_instance_offset",
            "collection_color",
            "parent_collection",
            "move_by_collection_offset",
            "triangulate_before_export",
            "triangulate_keep_normals",
            "apply_scale_before_export",
            "apply_rotation_before_export",
            "apply_transform_before_export",
            "pre_rotate_objects",
            "pre_rotate_euler",
        ]

        lines = ["import bpy", "scene = bpy.context.scene", ""]
        for prop in prop_names:
            value = getattr(prefs, prop, None)
            if value is None:
                continue
            if isinstance(value, bool):
                lines.append(f"scene.{prop} = {value}")
            elif isinstance(value, str):
                lines.append(f"scene.{prop} = {repr(value)}")
            elif hasattr(value, '__iter__'):
                lines.append(f"scene.{prop} = {tuple(value)}")
            else:
                lines.append(f"scene.{prop} = {value}")

        with open(filepath, 'w') as f:
            f.write("\n".join(lines) + "\n")

        self.report({'INFO'}, f"Preset saved: {filename}")
        return {'FINISHED'}


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

    def draw(self, context):
        from .preset_data_exporters import presets_simple_exporter
        builtin_names = set(presets_simple_exporter.keys())

        preset_dir = simple_export_presets_folder()
        if not os.path.isdir(preset_dir):
            self.layout.label(text="No presets found")
            return

        for fname in sorted(os.listdir(preset_dir)):
            if not fname.endswith('.py'):
                continue
            name = os.path.splitext(fname)[0]
            filepath = os.path.join(preset_dir, fname)
            icon = 'LOCKED' if name in builtin_names else 'NONE'
            op = self.layout.operator(self.preset_operator, text=name, icon=icon)
            op.filepath = filepath
            op.menu_idname = self.__class__.__name__


classes = (
    SceneExportPreset,
    SIMPLE_EXPORT_OT_ApplyPreset,
    SIMPLE_EXPORT_OT_set_default_preset,
    SIMPLE_EXPORT_OT_SavePresetFromPreferences,
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
