import os

import bpy
from bpy.app.handlers import persistent

from . import exporter_preset
from .preset_data_exporters import presets_simple_exporter
from .. import __package__ as base_package

files = [
    exporter_preset,
]


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
            preset_file.write("import bpy\n\n")
            preset_file.write("scene = bpy.context.scene\n\n")

            for key, value in preset_data.items():
                if isinstance(value, str):
                    # Escape backslashes for Python string literals
                    value = value.replace('\\', '\\\\')
                    preset_file.write(f"scene.{key} = '{value}'\n")
                else:
                    preset_file.write(f"scene.{key} = {value}\n")

    except IOError:
        pass  # Handle file write errors silently


def create_addon_preset_files(preset_data, preset_folder, saved_preset_files):
    if not preset_folder or not os.path.isdir(preset_folder):
        return

    for preset_name, preset in preset_data.items():
        if preset_name not in saved_preset_files:
            save_addon_presets(preset_name, preset_folder, preset)


@persistent
def load_preset_on_scene_open(dummy):
    # Access the add-on preferences
    addon_prefs = bpy.context.preferences.addons[base_package].preferences
    default_preset = addon_prefs.simple_export_default_preset

    if not default_preset:
        print("No default preset specified.")
        return

    # Get the presets folder path using the add-on's function
    from ..presets_addon.exporter_preset import simple_export_presets_folder
    presets_folder = simple_export_presets_folder()

    # Construct the preset file path
    preset_file = os.path.join(presets_folder, default_preset)
    if not os.path.exists(preset_file):
        print(f"Preset file not found: {preset_file}")
        return

    # Execute the preset using script.execute_preset
    from .exporter_preset import EXPORT_MT_scene_presets
    bpy.ops.script.execute_preset(filepath=preset_file, menu_idname=EXPORT_MT_scene_presets.__name__)
    print(f"Applied preset: {default_preset}")


def initialize_addon_presets():
    from ..presets_addon.exporter_preset import simple_export_presets_folder
    addon_preset_folder = simple_export_presets_folder()
    if not addon_preset_folder or not isinstance(addon_preset_folder, str):
        return
    print(f"Addon preset folder: {addon_preset_folder}")
    os.makedirs(addon_preset_folder, exist_ok=True)
    addon_preset_saved_preset_files = os.listdir(addon_preset_folder) if os.path.isdir(addon_preset_folder) else []
    create_addon_preset_files(presets_simple_exporter, addon_preset_folder, addon_preset_saved_preset_files)

    bpy.app.handlers.load_post.append(load_preset_on_scene_open)


def register():
    for file in files:
        file.register()
    initialize_addon_presets()


def unregister():
    for file in reversed(files):
        file.unregister()
