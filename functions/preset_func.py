import os


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


def _parse_prefix_preset_file(preset_path, prefix):
    """Parse a preset file extracting lines that start with 'prefix.'."""
    properties = {}
    if not os.path.exists(preset_path):
        return properties
    prefix_dot = prefix + "."
    with open(preset_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith(prefix_dot):
                try:
                    prop_name, prop_value = line[len(prefix_dot):].split(" = ", 1)
                    if prop_value.startswith(("'", '"')):
                        properties[prop_name] = prop_value.strip("'\"")
                    else:
                        properties[prop_name] = eval(prop_value)
                except Exception:
                    pass
    return properties


def _props_equal(blender_val, preset_val):
    """Compare a Blender property value with a parsed preset value."""
    try:
        # ENUM_FLAG properties (e.g. object_types) come back as Python sets
        if isinstance(blender_val, (set, frozenset)) or isinstance(preset_val, (set, frozenset)):
            return set(blender_val) == set(preset_val)
        # Blender vector/array/euler types have __len__ but aren't strings
        if hasattr(blender_val, '__len__') and not isinstance(blender_val, str):
            return tuple(blender_val) == tuple(preset_val)
        return blender_val == preset_val
    except Exception:
        return True  # assume equal if comparison is not possible


def format_preset_has_changes(collection, exporter):
    """Return True if the exporter's export properties differ from the stored format preset."""
    preset_name = getattr(collection, 'last_preset_name', '')
    if not preset_name:
        return False

    from ..core.export_formats import ExportFormats
    exporter_type = str(type(exporter.export_properties))
    key = ExportFormats.get_key_from_op_type(exporter_type)
    if not key:
        return False

    export_format_class = ExportFormats.get(key)
    subfolder = export_format_class.preset_subfolder

    from ..presets_export.preset_format_functions import get_preset_format_folder
    preset_file = os.path.join(get_preset_format_folder(), subfolder, f"{preset_name}.py")

    preset_props = parse_preset_file(preset_file)
    if not preset_props:
        return False

    for prop_name, preset_value in preset_props.items():
        if prop_name in ('filepath', 'use_selection'):
            continue
        if hasattr(exporter.export_properties, prop_name):
            if not _props_equal(getattr(exporter.export_properties, prop_name), preset_value):
                return True
    return False


def addon_preset_has_changes(collection, scene):
    """Return True if the scene properties differ from the stored addon preset."""
    preset_name = getattr(collection, 'last_addon_preset_name', '')
    if not preset_name:
        return False

    from ..presets_addon.exporter_preset import simple_export_presets_folder
    preset_file = os.path.join(simple_export_presets_folder(), f"{preset_name}.py")

    preset_props = _parse_prefix_preset_file(preset_file, "scene")
    if not preset_props:
        return False

    for prop_name, preset_value in preset_props.items():
        # Skip format preset file paths — machine-specific, handled by last_preset_name
        if prop_name.startswith('simple_export_preset_file_'):
            continue
        if hasattr(scene, prop_name):
            if not _props_equal(getattr(scene, prop_name), preset_value):
                return True
    return False


def collection_has_preset_changes(collection, exporter, scene):
    """Return True if either the format preset or addon preset has drifted for this collection."""
    return format_preset_has_changes(collection, exporter) or addon_preset_has_changes(collection, scene)



def assign_preset(exporter, preset_path):
    # Ensure the collection has exporters
    if not exporter:
        msg = "No valid exporter found"
        return False, msg

    if not preset_path:
        msg = "Please select a Preset"
        return False, msg

    def _assign_preset_to_exporter(properties, exporter):
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

    # Parse the preset file and remove filepath
    preset_properties = parse_preset_file(preset_path)

    if preset_properties:
        del preset_properties['filepath']

    # Apply the properties to the exporter
    _assign_preset_to_exporter(preset_properties, exporter)

    return True, None
