import os

import bpy

from .preset_data_fbx import presets_fbx
from .preset_data_gltf import presets_gltf
from ..core.export_formats import ExportFormats
from importlib import import_module

files = [
    # Add files here
]


def get_blender_version():
    return bpy.app.version


def get_versioned_module(version, preset_type):
    major, minor, _ = version
    if major == 5 and minor >= 0:
        return f".preset_data_{preset_type}_5_0"
    else:
        return f".preset_data_{preset_type}"


def save_export_presets(preset_name, preset_folder, preset_data):
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
            preset_file.write("op = bpy.context.active_operator\n\n")

            for key, value in preset_data.items():
                if isinstance(value, str):
                    preset_file.write(f"op.{key} = '{value}'\n")
                else:
                    preset_file.write(f"op.{key} = {value}\n")

    except IOError:
        pass  # Handle file write errors silently


def get_fbx_presets_folder():
    export_format = ExportFormats.get("FBX")
    return export_format.preset_folder


def get_gltf_presets_folder():
    export_format = ExportFormats.get("GLTF")
    return export_format.preset_folder


def create_export_preset_files(preset_data, preset_folder, saved_preset_files):
    if not preset_folder or not os.path.isdir(preset_folder):
        return

    for preset_name, preset in preset_data.items():
        if preset_name not in saved_preset_files:
            save_export_presets(preset_name, preset_folder, preset)


def initialize_presets():
    version = get_blender_version()
    for preset_type in ["fbx", "gltf"]:
        module_name = get_versioned_module(version, preset_type)
        try:
            presets_module = import_module(module_name, package=__package__)
        except ImportError:
            print(f"Warning: Could not import {module_name} for Blender {version}")
            continue

        preset_folder = globals()[f"get_{preset_type}_presets_folder"]()
        if not preset_folder or not isinstance(preset_folder, str):
            continue

        os.makedirs(preset_folder, exist_ok=True)
        saved_preset_files = os.listdir(preset_folder) if os.path.isdir(preset_folder) else []
        create_export_preset_files(getattr(presets_module, f"presets_{preset_type}"), preset_folder, saved_preset_files)


def register():
    for file in files:
        file.register()

    initialize_presets()


def unregister():
    for file in reversed(files):
        file.unregister()
