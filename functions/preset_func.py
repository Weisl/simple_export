import os
import re

# Fixed category for every built-in preset shipped with the addon (see
# presets_addon/preset_data_exporters.py). Highpoly/Lowpoly share one "Bake"
# category since they're a pipeline-stage pair, not separate destinations.
# Any preset name not listed here is user-saved and always goes to
# USER_ADDON_PRESET_CATEGORY, regardless of what it's named.
BUILTIN_ADDON_PRESET_CATEGORIES = {
    "Godot-default": "Godot",
    "Godot-animation": "Godot",
    "UE-default": "Unreal",
    "UE-animation": "Unreal",
    "Unity-default": "Unity",
    "Unity-animation": "Unity",
    "Highpoly-default": "Bake",
    "Lowpoly-default": "Bake",
    "USD-default": "USD",
    "USD-animation": "USD",
    "Basic-fbx-default": "Basic",
    "Basic-usd-default": "Basic",
    "Basic-abc-default": "Basic",
}
ADDON_PRESET_CATEGORY_ORDER = ["Basic", "Godot", "Bake", "Unreal", "USD", "Unity"]
USER_ADDON_PRESET_CATEGORY = "Custom"


def _sanitize_value_str(value_str):
    """Convert invalid mathutils repr like <Euler (x=...) ...> to a tuple before eval."""
    return re.sub(
        r"<\w+\s*\([^)]*\)[^>]*>",
        lambda m: "({})".format(", ".join(re.findall(r"[-+]?\d+\.?\d*(?:[eE][-+]?\d+)?", m.group(0)))),
        value_str
    )


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
                        properties[prop_name] = eval(_sanitize_value_str(prop_value))
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
                        properties[prop_name] = eval(_sanitize_value_str(prop_value))
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
        return False  # assume different if comparison fails so drift is visible


def format_preset_has_changes(collection, exporter):
    """Return True if the exporter's export properties differ from the stored format preset."""
    preset_name = getattr(collection, 'simple_export_export_preset', '')
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
    preset_name = getattr(collection, 'simple_export_addon_preset', '')
    if not preset_name:
        return False

    from ..presets_addon.exporter_preset import simple_export_presets_folder
    preset_file = os.path.join(simple_export_presets_folder(), f"{preset_name}.py")

    preset_props = _parse_prefix_preset_file(preset_file, "scene")
    if not preset_props:
        return False

    for prop_name, preset_value in preset_props.items():
        # Skip format preset file paths — machine-specific, handled by simple_export_export_preset
        if prop_name.startswith('simple_export_preset_file_'):
            continue
        if hasattr(scene, prop_name):
            if not _props_equal(getattr(scene, prop_name), preset_value):
                return True
    return False


def collection_has_preset_changes(collection, exporter, scene):
    """Return True if either the format preset or addon preset has drifted for this collection."""
    return format_preset_has_changes(collection, exporter) or addon_preset_has_changes(collection, scene)



def addon_preset_category_for_name(name):
    """Return the fixed category for a built-in preset name, or USER_ADDON_PRESET_CATEGORY
    for anything the user saved themselves (i.e. not shipped in preset_data_exporters.py)."""
    return BUILTIN_ADDON_PRESET_CATEGORIES.get(name, USER_ADDON_PRESET_CATEGORY)


def list_addon_presets_by_category():
    """Group every addon preset (.py file in the presets folder) by its fixed category.

    This is the single source of truth for "what addon presets exist and which
    category do they belong to" — every UI that lists or filters addon presets
    (the two collection-setup dialogs, the preset picker menu, the preferences
    preset manager) should read from this instead of re-scanning the folder.

    Returns:
        dict: {category: [(name, filepath, is_builtin), ...]}, only containing
        categories that currently have presets.
    """
    from ..presets_addon.exporter_preset import simple_export_presets_folder
    from ..presets_addon.preset_data_exporters import presets_simple_exporter
    builtin_names = set(presets_simple_exporter.keys())

    folder = simple_export_presets_folder()
    grouped = {}
    if os.path.isdir(folder):
        for fname in sorted(os.listdir(folder)):
            if fname.endswith('.py'):
                name = os.path.splitext(fname)[0]
                filepath = os.path.join(folder, fname)
                category = addon_preset_category_for_name(name)
                grouped.setdefault(category, []).append((name, filepath, name in builtin_names))
    return grouped


def list_addon_preset_names_by_category():
    """Group every addon preset by category, names only.

    Returns:
        dict: {category: [preset_name, ...]}, only containing categories that have presets.
    """
    return {
        category: [name for name, _filepath, _is_builtin in entries]
        for category, entries in list_addon_presets_by_category().items()
    }


def get_addon_preset_category_items(self, context):
    """EnumProperty items callback: categories that currently have presets, built-ins first."""
    grouped = list_addon_preset_names_by_category()
    order = [c for c in ADDON_PRESET_CATEGORY_ORDER if c in grouped]
    if USER_ADDON_PRESET_CATEGORY in grouped:
        order.append(USER_ADDON_PRESET_CATEGORY)
    items = [(category, category, "") for category in order]
    return items if items else [('NONE', "No Presets Available", "")]


def get_addon_preset_items_for_category(self, context):
    """EnumProperty items callback: presets belonging to self.addon_preset_category."""
    grouped = list_addon_preset_names_by_category()
    names = grouped.get(self.addon_preset_category, [])
    items = [(name, name, "") for name in names]
    return items if items else [('NONE', "No Presets Available", "")]


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
        preset_properties.pop('filepath', None)  # skip gracefully if key absent

    # Apply the properties to the exporter
    _assign_preset_to_exporter(preset_properties, exporter)

    return True, None
