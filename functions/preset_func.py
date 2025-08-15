import os

import bpy

from .. import __package__ as base_package


def get_presets_folder():
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


def parse_preset_file(preset_path):
    """Parse the preset file to extract properties and their values."""
    properties = {}

    if not os.path.exists(preset_path):
        print(f"Preset file not found: {preset_path}")
        return properties

    with open(preset_path, 'r') as preset_file:
        for line in preset_file:
            line = line.strip()
            if line.startswith("op."):
                try:
                    # Extract the property name and value
                    prop_name, prop_value = line[3:].split(" = ", 1)
                    # Evaluate the value if it's not a string
                    if prop_value.startswith(("'", '"')):
                        properties[prop_name] = prop_value.strip("'\"")
                    else:
                        properties[prop_name] = eval(prop_value)
                except Exception as e:
                    print(f"Error parsing line: {line} -> {e}")
    return properties


def assign_preset_to_exporter(properties, exporter):
    """Apply parsed properties to the exporter."""
    for prop_name, prop_value in properties.items():
        # ignore filepath
        if prop_name in ['filepath', 'use_selection']:
            # print(f"Preset property '{prop_name}' ignored.")
            continue

        try:
            if hasattr(exporter.export_properties, prop_name):
                setattr(exporter.export_properties, prop_name, prop_value)
            else:
                print(f"Exporter property '{prop_name}' not found.")
        except Exception as e:
            print(f"Error setting property '{prop_name}': {e}")


def assign_preset(exporter, preset_path):
    # Ensure the collection has exporters
    if not exporter:
        msg = "No valid exporter found"
        return False, msg

    if not preset_path:
        msg = "Please select a Preset"
        return False, msg

    # Parse the preset file and remove filepath
    preset_properties = parse_preset_file(preset_path)

    if preset_properties:
        del preset_properties['filepath']

    # Apply the properties to the exporter
    assign_preset_to_exporter(preset_properties, exporter)

    return True, None
