import bpy
import os
from bl_operators.presets import AddPresetBase
from bpy.types import Menu
from bpy.types import Operator

from .. import __package__ as base_package
from ..core.export_formats import get_export_format_items
from ..functions.preset_func import (
    list_addon_presets_by_category,
    parse_addon_preset_file,
    is_builtin_addon_preset,
    ADDON_PRESET_CATEGORY_ORDER,
    USER_ADDON_PRESET_CATEGORY,
)

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
        # Root object appearance
        "scene.root_empty_display_type",
        "scene.root_empty_display_size",
        "scene.root_empty_show_name",
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

    export_format: bpy.props.EnumProperty(
        name="Format",
        description="Export format this preset applies to",
        items=get_export_format_items(),
        default='FBX',
    )

    def invoke(self, context, event):
        if not self.remove_active:
            context.scene.export_format = self.export_format
        return super().invoke(context, event)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "export_format")
        layout.prop(self, "name")

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


# The Presets tab of the addon preferences edits presets through the preferences'
# own copy of the preset properties (the "editor"). A preset file stores the same
# property names on the scene. Selecting, saving and updating only ever touch the
# editor and the preset files, never the scene or the N panel's selected preset.
_EDITOR_PROP_NAMES = [value.split(".", 1)[1] for value in BaseExportPreset.preset_values]

LOCKED_PRESET_MESSAGE = "Built-in presets are locked and restored on every addon update. Duplicate it to customise it"


def _preset_name(filepath):
    return os.path.splitext(os.path.basename(filepath))[0]


def _preset_filepath_for_name(name):
    """Path of the preset file for a name typed by the user, or None if the name is unusable."""
    name = name.strip()
    if not name or "/" in name or "\\" in name:
        return None
    return os.path.join(simple_export_presets_folder(), name.replace(" ", "_") + ".py")


def _new_preset_filepath(name):
    """(filepath, problem) for a name typed for a *new* preset. problem is '' when the name is usable,
    otherwise a message for the user and filepath is None."""
    filepath = _preset_filepath_for_name(name)
    if filepath is None:
        return None, "Preset name cannot be empty or contain slashes."
    preset_name = _preset_name(filepath)
    if is_builtin_addon_preset(preset_name):
        return None, f"'{preset_name}' is a built-in preset name. Choose another name."
    if os.path.exists(filepath):
        return None, f"A preset named '{preset_name}' already exists. Choose another name, or select it and Update it."
    return filepath, ""


def _unique_preset_name(base):
    """base, or 'base 2', 'base 3'... - the first name that is free for a new preset."""
    name = base
    for number in range(2, 1000):
        if not _new_preset_filepath(name)[1]:
            break
        name = f"{base} {number}"
    return name


# What the editor held right after the selected preset was loaded from / written to its file,
# as {filepath: snapshot}. Comparing it with the editor's current values is what tells the
# Presets tab that there are unsaved edits. Only ever holds the one preset being edited.
_editor_baseline = {}


def _editor_snapshot(prefs):
    snapshot = {}
    for prop in _EDITOR_PROP_NAMES:
        try:
            value = getattr(prefs, prop)
        except AttributeError:
            continue
        if isinstance(value, (set, frozenset)):  # ENUM_FLAG properties
            value = frozenset(value)
        elif not isinstance(value, str) and hasattr(value, '__len__'):  # vector / array properties
            value = tuple(value)
        snapshot[prop] = value
    return snapshot


def _remember_editor_state(prefs, filepath):
    _editor_baseline.clear()
    _editor_baseline[filepath] = _editor_snapshot(prefs)


def editor_has_changes(prefs, filepath):
    """True if the editor differs from what the preset at filepath had when it was loaded or last saved."""
    baseline = _editor_baseline.get(filepath)
    return baseline is not None and baseline != _editor_snapshot(prefs)


def load_preset_into_editor(prefs, filepath):
    """Copy a preset file's values into the preferences editor. The scene and the N panel's
    selected preset are not touched."""
    _sanitize_preset_file(filepath)
    values = parse_addon_preset_file(filepath)
    for prop in _EDITOR_PROP_NAMES:
        # Reset first so a preset that predates a property doesn't inherit the previous preset's value.
        try:
            prefs.property_unset(prop)
        except (AttributeError, TypeError):
            continue
        if prop in values:
            try:
                setattr(prefs, prop, values[prop])
            except (AttributeError, TypeError, ValueError):
                pass
    _remember_editor_state(prefs, filepath)


def write_preset_from_editor(prefs, filepath):
    """Write the preferences editor's values to filepath as an addon preset."""
    lines = ["import bpy", "scene = bpy.context.scene", ""]
    for prop in _EDITOR_PROP_NAMES:
        value = getattr(prefs, prop, None)
        if value is None:
            continue
        if not isinstance(value, str) and hasattr(value, '__iter__'):
            value = tuple(value)
        lines.append(f"scene.{prop} = {value!r}")

    with open(filepath, 'w') as f:
        f.write("\n".join(lines) + "\n")
    _remember_editor_state(prefs, filepath)


def _editing_preset_path(context):
    """Path of the preset selected in the Presets tab if it still exists, else ''."""
    path = context.window_manager.simple_export_editing_preset
    return path if path and os.path.isfile(path) else ""


class SIMPLE_EXPORT_OT_SelectPresetForEditing(bpy.types.Operator):
    """Load this preset into the settings below so it can be edited. The scene and the preset chosen in the N panel are not affected"""
    bl_idname = "simple_export.select_preset_for_editing"
    bl_label = "Edit Preset"
    bl_options = {'REGISTER', 'INTERNAL'}

    filepath: bpy.props.StringProperty()

    @classmethod
    def description(cls, context, properties):
        # Selecting the preset that is already being edited is how the Presets tab reverts it.
        if properties.filepath and properties.filepath == context.window_manager.simple_export_editing_preset:
            return "Discard the unsaved changes and reload this preset from its file"
        return cls.__doc__

    def execute(self, context):
        if not os.path.isfile(self.filepath):
            self.report({'ERROR'}, "Preset file not found.")
            return {'CANCELLED'}
        prefs = context.preferences.addons[base_package].preferences
        load_preset_into_editor(prefs, self.filepath)
        context.window_manager.simple_export_editing_preset = self.filepath
        return {'FINISHED'}


class SIMPLE_EXPORT_OT_SavePresetFromPreferences(bpy.types.Operator):
    """Save the settings below as a new preset"""
    bl_idname = "simple_export.save_preset_from_preferences"
    bl_label = "Save as New Preset"
    bl_options = {'REGISTER', 'INTERNAL'}

    name: bpy.props.StringProperty(
        name="Preset Name",
        description="Name for the new preset",
        default="My Preset",
    )

    def invoke(self, context, event):
        editing = _editing_preset_path(context)
        self.name = _unique_preset_name(f"Copy of {_preset_name(editing)}" if editing else "My Preset")
        return context.window_manager.invoke_props_dialog(self, width=360)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.activate_init = True  # type the name straight away
        row.prop(self, "name")
        problem = _new_preset_filepath(self.name)[1]
        if problem:
            layout.label(text=problem, icon='ERROR')

    def execute(self, context):
        filepath, problem = _new_preset_filepath(self.name)
        if problem:
            self.report({'WARNING'}, problem)
            return {'CANCELLED'}

        prefs = context.preferences.addons[base_package].preferences
        write_preset_from_editor(prefs, filepath)
        context.window_manager.simple_export_editing_preset = filepath
        self.report({'INFO'}, f"Preset saved: {_preset_name(filepath)}")
        return {'FINISHED'}


class SIMPLE_EXPORT_OT_UpdatePreset(bpy.types.Operator):
    """Overwrite the selected preset with the settings below"""
    bl_idname = "simple_export.update_preset"
    bl_label = "Update Preset"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        path = _editing_preset_path(context)
        if not path:
            cls.poll_message_set("Select a preset to edit first")
            return False
        if is_builtin_addon_preset(_preset_name(path)):
            cls.poll_message_set(LOCKED_PRESET_MESSAGE)
            return False
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        name = _preset_name(_editing_preset_path(context))
        self.layout.label(text=f"Overwrite '{name}' with the settings below?")

    def execute(self, context):
        path = _editing_preset_path(context)
        prefs = context.preferences.addons[base_package].preferences
        write_preset_from_editor(prefs, path)
        self.report({'INFO'}, f"Preset updated: {_preset_name(path)}")
        return {'FINISHED'}


class SIMPLE_EXPORT_OT_RemovePreset(bpy.types.Operator):
    """Delete the selected preset"""
    bl_idname = "simple_export.remove_preset"
    bl_label = "Remove Preset"
    bl_options = {'REGISTER', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        path = _editing_preset_path(context)
        if not path:
            cls.poll_message_set("Select a preset to edit first")
            return False
        if is_builtin_addon_preset(_preset_name(path)):
            cls.poll_message_set(LOCKED_PRESET_MESSAGE)
            return False
        return True

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        name = _preset_name(_editing_preset_path(context))
        self.layout.label(text=f"Delete preset '{name}'?")

    def execute(self, context):
        path = _editing_preset_path(context)
        try:
            os.remove(path)
        except OSError as e:
            self.report({'ERROR'}, f"Could not delete preset: {e}")
            return {'CANCELLED'}
        context.window_manager.simple_export_editing_preset = ""
        if context.scene.simple_export_selected_preset == path:
            context.scene.simple_export_selected_preset = ""
        self.report({'INFO'}, f"Preset removed: {_preset_name(path)}")
        return {'FINISHED'}


class SIMPLE_EXPORT_OT_DuplicatePreset(bpy.types.Operator):
    """Copy the selected preset under a new name and select the copy for editing"""
    bl_idname = "simple_export.duplicate_preset"
    bl_label = "Duplicate Preset"
    bl_options = {'REGISTER', 'INTERNAL'}

    name: bpy.props.StringProperty(name="New Preset Name", default="", description="Name for the duplicated preset")
    source_path: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    @classmethod
    def poll(cls, context):
        if not _editing_preset_path(context):
            cls.poll_message_set("Select a preset to edit first")
            return False
        return True

    def invoke(self, context, event):
        self.source_path = _editing_preset_path(context)
        self.name = _unique_preset_name(f"Copy of {_preset_name(self.source_path)}")
        return context.window_manager.invoke_props_dialog(self, width=360)

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.activate_init = True  # type the name straight away
        row.prop(self, "name")
        problem = _new_preset_filepath(self.name)[1]
        if problem:
            layout.label(text=problem, icon='ERROR')

    def execute(self, context):
        filepath, problem = _new_preset_filepath(self.name)
        if problem:
            self.report({'WARNING'}, problem)
            return {'CANCELLED'}
        if not self.source_path or not os.path.isfile(self.source_path):
            self.report({'WARNING'}, "Source preset not found.")
            return {'CANCELLED'}

        import shutil
        shutil.copy2(self.source_path, filepath)

        prefs = context.preferences.addons[base_package].preferences
        load_preset_into_editor(prefs, filepath)
        context.window_manager.simple_export_editing_preset = filepath
        self.report({'INFO'}, f"Preset duplicated as: {_preset_name(filepath)}")
        return {'FINISHED'}


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
        return {'FINISHED'}


class EXPORT_MT_scene_presets(Menu):
    bl_label = "Export Format Presets"
    preset_subdir = BaseExportPreset.preset_subdir
    preset_operator = "simple_export.apply_preset"

    def draw(self, context):
        layout = self.layout
        grouped = list_addon_presets_by_category()

        for category in [*ADDON_PRESET_CATEGORY_ORDER, USER_ADDON_PRESET_CATEGORY]:
            entries = grouped.get(category, [])
            layout.menu(f"EXPORT_MT_scene_presets_{category}", text=f"{category} ({len(entries)})")

        layout.separator()
        op = layout.operator(SceneExportPreset.bl_idname, text="New Preset...", icon='ADD')
        op.export_format = context.scene.export_format


def _draw_apply_entry(layout, context, name, filepath, is_builtin):
    """Menu row that applies the preset to the scene (the N panel's preset menu)."""
    op = layout.operator("simple_export.apply_preset", text=name, icon='LOCKED' if is_builtin else 'NONE')
    op.filepath = filepath
    op.menu_idname = EXPORT_MT_scene_presets.__name__


def _draw_edit_entry(layout, context, name, filepath, is_builtin):
    """Menu row that loads the preset into the Presets tab for editing (never applies it)."""
    prefs = context.preferences.addons[base_package].preferences
    is_default = filepath == prefs.simple_export_default_preset
    op = layout.operator("simple_export.select_preset_for_editing",
                         text=f"{name}  (default)" if is_default else name,
                         icon='LOCKED' if is_builtin else 'NONE',
                         depress=filepath == context.window_manager.simple_export_editing_preset)
    op.filepath = filepath


def _make_category_preset_menu(category, idname_prefix="EXPORT_MT_scene_presets", draw_entry=_draw_apply_entry):
    """Build a Menu subclass listing one preset category's addon presets, one row per preset drawn by draw_entry."""

    class _CategoryPresetsMenu(Menu):
        bl_idname = f"{idname_prefix}_{category}"
        bl_label = category

        def draw(self, context):
            layout = self.layout
            entries = list_addon_presets_by_category().get(category, [])

            if entries:
                for name, filepath, is_builtin in entries:
                    draw_entry(layout, context, name, filepath, is_builtin)
            else:
                layout.label(text="No presets yet", icon='INFO')

    _CategoryPresetsMenu.__name__ = f"{idname_prefix}_{category}"
    _CategoryPresetsMenu.__qualname__ = _CategoryPresetsMenu.__name__
    return _CategoryPresetsMenu


CATEGORY_PRESET_MENU_CLASSES = tuple(
    _make_category_preset_menu(category)
    for category in [*ADDON_PRESET_CATEGORY_ORDER, USER_ADDON_PRESET_CATEGORY]
)


class SIMPLE_EXPORT_MT_edit_preset(Menu):
    """The Presets tab's one-row preset picker: choose which preset to edit (nothing is applied to the scene)"""
    bl_label = "Select Preset"

    def draw(self, context):
        layout = self.layout
        grouped = list_addon_presets_by_category()
        for category in [*ADDON_PRESET_CATEGORY_ORDER, USER_ADDON_PRESET_CATEGORY]:
            entries = grouped.get(category, [])
            if entries:
                layout.menu(f"{EDIT_MENU_PREFIX}_{category}", text=f"{category} ({len(entries)})")
        if not grouped:
            layout.label(text="No presets yet", icon='INFO')


EDIT_MENU_PREFIX = SIMPLE_EXPORT_MT_edit_preset.__name__

EDIT_PRESET_MENU_CLASSES = tuple(
    _make_category_preset_menu(category, idname_prefix=EDIT_MENU_PREFIX, draw_entry=_draw_edit_entry)
    for category in [*ADDON_PRESET_CATEGORY_ORDER, USER_ADDON_PRESET_CATEGORY]
)


classes = (
    SceneExportPreset,
    SIMPLE_EXPORT_OT_ApplyPreset,
    SIMPLE_EXPORT_OT_SelectPresetForEditing,
    SIMPLE_EXPORT_OT_DuplicatePreset,
    SIMPLE_EXPORT_OT_SavePresetFromPreferences,
    SIMPLE_EXPORT_OT_UpdatePreset,
    SIMPLE_EXPORT_OT_RemovePreset,
    *CATEGORY_PRESET_MENU_CLASSES,
    EXPORT_MT_scene_presets,
    *EDIT_PRESET_MENU_CLASSES,
    SIMPLE_EXPORT_MT_edit_preset,
)


# Register and Unregister
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    # Session-only: which preset the Presets tab of the addon preferences is editing.
    # Deliberately separate from Scene.simple_export_selected_preset (the N panel's choice).
    bpy.types.WindowManager.simple_export_editing_preset = bpy.props.StringProperty(
        name="Preset Being Edited",
        description="Path of the preset loaded into the Presets tab of the addon preferences",
        default="",
        options={'HIDDEN', 'SKIP_SAVE'},
    )


def unregister():
    from bpy.utils import unregister_class
    if hasattr(bpy.types.WindowManager, 'simple_export_editing_preset'):
        del bpy.types.WindowManager.simple_export_editing_preset
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)


if __name__ == "__main__":
    register()
