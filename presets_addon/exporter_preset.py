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
        # Export format
        "scene.export_format",
        # Export folder path
        "scene.export_folder_mode",
        "scene.folder_path_absolute",
        "scene.folder_path_relative",
        "scene.folder_path_search",
        "scene.folder_path_replace",
        # File name
        "scene.filename_prefix",
        "scene.filename_suffix",
        "scene.filename_separator",
        "scene.filename_blend_prefix",
        # Format-specific export preset files
        "scene.simple_export_preset_file_fbx",
        "scene.simple_export_preset_file_obj",
        "scene.simple_export_preset_file_gltf",
        "scene.simple_export_preset_file_usd",
        "scene.simple_export_preset_file_abc",
        "scene.simple_export_preset_file_ply",
        "scene.simple_export_preset_file_stl",
        # Collection name
        "scene.collection_prefix",
        "scene.collection_suffix",
        "scene.collection_separator",
        "scene.collection_blend_prefix",
        # Collection settings
        "scene.parent_collection",
        "scene.collection_color",
        "scene.use_root_object",
        "scene.collection_instance_offset",
        "scene.set_export_path",
        "scene.assign_preset",
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


def _sanitize_preset_file(preset_path):
    import re
    if not os.path.exists(preset_path):
        return
    with open(preset_path, 'r') as f:
        content = f.read()
    # Blender writes mathutils types (Euler, Vector, Color, Quaternion) as
    # "<TypeName (key=val, ...) [extra]>" which is invalid Python — convert to tuple
    def _to_tuple(match):
        numbers = re.findall(r"[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?", match.group(1))
        return f"= ({', '.join(numbers)})"
    fixed = re.sub(r"= (<\w+\s*\([^)]*\)[^>]*>)", _to_tuple, content)

    # Fix stale Blender-version-specific preset paths (e.g. blender/5.0/... → blender/5.1/...)
    # These are stored as enum values and must match the paths in the current Blender install.
    import bpy
    current_op_folder = os.path.join(bpy.utils.resource_path('USER'), "scripts", "presets", "operator")
    _OPERATOR_MARKER = "/scripts/presets/operator/"

    def _fix_preset_path(match):
        old_path = match.group(2)
        norm = old_path.replace("\\", "/")
        idx = norm.find(_OPERATOR_MARKER)
        if idx == -1:
            return match.group(0)
        rel = norm[idx + len(_OPERATOR_MARKER):]
        new_path = os.path.join(current_op_folder, *rel.split("/"))
        if os.path.exists(new_path) and new_path != old_path:
            return f"= {repr(new_path)}"
        return match.group(0)

    fixed = re.sub(r"= (['\"])(.+?/scripts/presets/operator/.+?)\1", _fix_preset_path, fixed)

    if fixed != content:
        with open(preset_path, 'w') as f:
            f.write(fixed)


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
            _sanitize_preset_file(preset_path)
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
            # Export format
            "export_format",
            # Export folder path
            "export_folder_mode",
            "folder_path_absolute",
            "folder_path_relative",
            "folder_path_search",
            "folder_path_replace",
            # File name
            "filename_prefix",
            "filename_suffix",
            "filename_separator",
            "filename_blend_prefix",
            # Format-specific export preset files
            "simple_export_preset_file_fbx",
            "simple_export_preset_file_obj",
            "simple_export_preset_file_gltf",
            "simple_export_preset_file_usd",
            "simple_export_preset_file_abc",
            "simple_export_preset_file_ply",
            "simple_export_preset_file_stl",
            # Collection name
            "collection_prefix",
            "collection_suffix",
            "collection_separator",
            "collection_blend_prefix",
            # Collection settings
            "parent_collection",
            "collection_color",
            "use_root_object",
            "collection_instance_offset",
            "set_export_path",
            "assign_preset",
            # Pre-export operations
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


_PRESET_PROP_NAMES = [
    "export_format",
    "export_folder_mode",
    "folder_path_absolute",
    "folder_path_relative",
    "folder_path_search",
    "folder_path_replace",
    "filename_prefix",
    "filename_suffix",
    "filename_blend_prefix",
    "simple_export_preset_file_fbx",
    "simple_export_preset_file_obj",
    "simple_export_preset_file_gltf",
    "simple_export_preset_file_usd",
    "simple_export_preset_file_abc",
    "simple_export_preset_file_ply",
    "simple_export_preset_file_stl",
    "collection_prefix",
    "collection_suffix",
    "collection_blend_prefix",
    "parent_collection",
    "collection_color",
    "use_root_object",
    "collection_instance_offset",
    "set_export_path",
    "assign_preset",
    "move_by_collection_offset",
    "triangulate_before_export",
    "triangulate_keep_normals",
    "apply_scale_before_export",
    "apply_rotation_before_export",
    "apply_transform_before_export",
    "pre_rotate_objects",
    "pre_rotate_euler",
]


def _sync_scene_to_prefs(context):
    """Copy preset-relevant scene properties into addon preferences."""
    try:
        prefs = context.preferences.addons[ADDON_NAME].preferences
        scene = context.scene
        for prop in _PRESET_PROP_NAMES:
            if not hasattr(scene, prop) or not hasattr(prefs, prop):
                continue
            try:
                val = getattr(scene, prop)
                if hasattr(val, '__len__') and not isinstance(val, str):
                    setattr(prefs, prop, tuple(val))
                else:
                    setattr(prefs, prop, val)
            except Exception:
                pass
    except Exception:
        pass


class SIMPLE_EXPORT_OT_ApplyPreset(bpy.types.Operator):
    """Apply an export format preset and track it as the currently selected preset"""
    bl_idname = "simple_export.apply_preset"
    bl_label = "Apply Export Format Preset"
    bl_options = {'REGISTER', 'INTERNAL'}

    filepath: bpy.props.StringProperty()
    menu_idname: bpy.props.StringProperty()

    def execute(self, context):
        _sanitize_preset_file(self.filepath)
        try:
            bpy.ops.script.execute_preset(
                filepath=self.filepath,
                menu_idname=EXPORT_MT_scene_presets.__name__,
            )
        except Exception as e:
            self.report({'ERROR'}, f"Could not apply preset: {e}")
            return {'CANCELLED'}
        context.scene.simple_export_selected_preset = self.filepath
        _sync_scene_to_prefs(context)
        return {'FINISHED'}


class SIMPLE_EXPORT_OT_DuplicatePreset(bpy.types.Operator):
    """Duplicate the currently selected preset as a starting point for a new one"""
    bl_idname = "simple_export.duplicate_preset"
    bl_label = "Duplicate Preset"
    bl_options = {'REGISTER', 'INTERNAL'}

    name: bpy.props.StringProperty(name="New Preset Name", default="")
    source_path: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    def invoke(self, context, event):
        selected = context.scene.simple_export_selected_preset
        if not selected or not os.path.exists(selected):
            self.report({'WARNING'}, "No preset selected. Apply a preset first.")
            return {'CANCELLED'}
        self.source_path = selected
        base = os.path.splitext(os.path.basename(selected))[0]
        self.name = f"Copy of {base}"
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "name")

    def execute(self, context):
        name = self.name.strip()
        if not name:
            self.report({'WARNING'}, "Preset name cannot be empty.")
            return {'CANCELLED'}
        if not self.source_path or not os.path.exists(self.source_path):
            self.report({'WARNING'}, "Source preset not found.")
            return {'CANCELLED'}

        import shutil
        preset_dir = simple_export_presets_folder()
        filename = name.replace(" ", "_") + ".py"
        filepath = os.path.join(preset_dir, filename)
        shutil.copy2(self.source_path, filepath)

        bpy.ops.simple_export.apply_preset(filepath=filepath, menu_idname=EXPORT_MT_scene_presets.__name__)
        self.report({'INFO'}, f"Preset duplicated as: {filename}")
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
    SIMPLE_EXPORT_OT_DuplicatePreset,
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
