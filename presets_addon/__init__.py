import os

import bpy
from bpy.app.handlers import persistent

from . import exporter_preset
from .preset_data_exporters import presets_simple_exporter
from .. import __package__ as base_package
from ..core.info import DEFAULT_ADDON_PRESET

files = [
    exporter_preset,
]


def _render_addon_preset(preset_data):
    """Return the source text of an addon preset file for the given preset dict."""
    lines = ["import bpy", "", "scene = bpy.context.scene", ""]
    for key, value in preset_data.items():
        if isinstance(value, str):
            lines.append(f"scene.{key} = {repr(value)}")
        else:
            lines.append(f"scene.{key} = {value}")
    return "\n".join(lines) + "\n"


def save_addon_presets(preset_name, preset_folder, preset_data):
    """
    Save the given preset as a Blender preset.

    Args:
        preset_name (str): The name of the preset.
        preset_folder (str): The folder where the preset should be saved.
        preset_data (dict): The preset containing preference settings.

    Returns:
        None
    """
    if not isinstance(preset_folder, str):
        return

    if not isinstance(preset_data, dict):
        return

    os.makedirs(preset_folder, exist_ok=True)

    preset_file_path = os.path.join(preset_folder, f'{preset_name}.py')

    try:
        with open(preset_file_path, 'w', encoding='utf-8') as preset_file:
            preset_file.write(_render_addon_preset(preset_data))
    except IOError:
        pass  # Handle file write errors silently


def create_addon_preset_files(preset_data, preset_folder):
    """Write every built-in preset to preset_folder, replacing files that are missing or
    differ from the shipped version. Built-ins are locked in the UI, so this is how an
    addon update (or a hand-edited file) is brought back in line with the addon."""
    if not preset_folder or not os.path.isdir(preset_folder):
        return

    for preset_name, preset in preset_data.items():
        if not isinstance(preset, dict):
            continue
        preset_file_path = os.path.join(preset_folder, f'{preset_name}.py')
        try:
            with open(preset_file_path, 'r', encoding='utf-8') as preset_file:
                current = preset_file.read()
        except (IOError, UnicodeDecodeError):
            current = None
        if current != _render_addon_preset(preset):
            save_addon_presets(preset_name, preset_folder, preset)


def pin_default_preset_if_unset(addon_prefs):
    """Select DEFAULT_ADDON_PRESET as the default preset unless the user already chose one.

    The enum's built-in default is an index baked in at import time. On a fresh
    install the preset folder is still empty then, so the index falls back to 0 and
    points at whichever file the folder listing happens to return first.
    """
    if addon_prefs.is_property_set("simple_export_default_preset"):
        return
    from ..preferences.preferenecs import get_simple_export_preset_files
    for filepath, filename, _description in get_simple_export_preset_files(addon_prefs, bpy.context):
        if filename == f"{DEFAULT_ADDON_PRESET}.py":
            addon_prefs.simple_export_default_preset = filepath
            return


def apply_default_preset():
    """Apply the default export format preset to the current scene and update the selection tracker."""
    try:
        addon_prefs = bpy.context.preferences.addons[base_package].preferences
        if addon_prefs is None:
            return
        pin_default_preset_if_unset(addon_prefs)
        default_preset = addon_prefs.simple_export_default_preset
        if not default_preset or not os.path.exists(default_preset):
            return
        from .exporter_preset import EXPORT_MT_scene_presets, _sanitize_preset_file
        _sanitize_preset_file(default_preset)
        bpy.ops.script.execute_preset(filepath=default_preset, menu_idname=EXPORT_MT_scene_presets.__name__)
        bpy.context.scene.simple_export_selected_preset = default_preset
    except Exception as e:
        print(f"[Simple Export] Could not apply default preset: {e}")


@persistent
def load_preset_on_scene_open(dummy):
    apply_default_preset()


def initialize_addon_presets():
    from ..presets_addon.exporter_preset import simple_export_presets_folder
    addon_preset_folder = simple_export_presets_folder()
    if not addon_preset_folder or not isinstance(addon_preset_folder, str):
        return
    # print(f"Addon preset folder: {addon_preset_folder}")
    os.makedirs(addon_preset_folder, exist_ok=True)
    create_addon_preset_files(presets_simple_exporter, addon_preset_folder)

    bpy.app.handlers.load_post.append(load_preset_on_scene_open)


def register():
    for file in files:
        file.register()
    initialize_addon_presets()
    bpy.app.timers.register(apply_default_preset, first_interval=0.1)


def unregister():
    for file in reversed(files):
        file.unregister()
