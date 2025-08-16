import bpy
import os

from .. import __package__ as base_package


def get_format_preset_filepath(element, export_format):
    # Find the property for the current export format
    prop_name = f"simple_export_preset_file_{export_format.lower()}"

    from ..core.export_formats import ExportFormats

    export_format_class = ExportFormats.get(export_format)

    subfolder = export_format_class.preset_subfolder
    preset_path = os.path.join(get_preset_format_folder(), f"{subfolder}")
    preset_file = os.path.join(preset_path, str(getattr(element, prop_name)))

    return preset_file


def get_preset_format_folder():
    """Retrieve the preset folder, using override if set, else default to Blender's location."""
    try:
        # Attempt to get the preferences and custom preset path
        prefs = bpy.context.preferences.addons.get(base_package)
        if prefs and hasattr(prefs, 'preferences') and hasattr(prefs.preferences, 'preset_path_override'):
            preset_path_override = prefs.preferences.preset_path_override
            if preset_path_override and os.path.isdir(preset_path_override):
                return preset_path_override
    except Exception:
        # Avoid printing to prevent potential recursion issues
        pass

    # Default Blender location
    return os.path.join(bpy.utils.resource_path('USER'), "scripts", "presets", "operator")
