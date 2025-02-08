import bpy
import os


def get_presets_folder():
    """Retrieve the base path for Blender's presets folder."""
    # Get the user scripts folder dynamically
    return os.path.join(bpy.utils.resource_path('USER'), "scripts", "presets", "operator")


EXPORT_FORMATS = {
    "FBX": {
        "op_name": "IO_FH_fbx",
        "label": "FBX",
        "description": "FBX Export",
        "preset_folder": os.path.join(get_presets_folder(), "export_scene.fbx"),
        "op_type": "<class 'bpy.types.EXPORT_SCENE_OT_fbx'>",
        "file_extension": "fbx",
    },
    "OBJ": {
        "op_name": "IO_FH_obj",
        "label": "OBJ",
        "description": "Wavefront OBJ Export",
        "preset_folder": os.path.join(get_presets_folder(), "wm.obj_export"),
        "op_type": "<class 'bpy.types.WM_OT_obj_export'>",
        "file_extension": "obj",
    },
    "GLTF": {
        "op_name": "IO_FH_gltf2",
        "label": "glTF",
        "description": "glTF 2.0 Export",
        "preset_folder": os.path.join(get_presets_folder(), "export_scene.gltf"),
        "op_type": "<class 'bpy.types.EXPORT_SCENE_OT_gltf'>",
        "file_extension": "glb",
    },
    "USD": {
        "op_name": "IO_FH_usd",
        "label": "USD",
        "description": "Universal Scene Description Export",
        "preset_folder": os.path.join(get_presets_folder(), "wm.usd_export"),
        "op_type": "<class 'bpy.types.WM_OT_usd_export'>",
        "file_extension": "usd",
    },
    "ABC": {
        "op_name": "IO_FH_alembic",
        "label": "Alembic",
        "description": "Alembic Export",
        "preset_folder": os.path.join(get_presets_folder(), "wm.alembic_export"),
        "op_type": "<class 'bpy.types.WM_OT_alembic_export'>",
        "file_extension": "abc",
    },
    "PLY": {
        "op_name": "IO_FH_ply",
        "label": "PLY",
        "description": "Stanford PLY Export",
        "preset_folder": os.path.join(get_presets_folder(), "wm.ply_export"),
        "op_type": "<class 'bpy.types.WM_OT_ply_export'>",
        "file_extension": "ply",
    },
    "STL": {
        "op_name": "IO_FH_stl",
        "label": "STL",
        "description": "STL Export",
        "preset_folder": os.path.join(get_presets_folder(), "wm.stl_export"),
        "op_type": "<class 'bpy.types.WM_OT_stl_export'>",
        "file_extension": "stl",
    },
}


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
    if not preset_properties:
        del preset_properties['filepath']

    # Apply the properties to the exporter
    assign_preset_to_exporter(preset_properties, exporter)

    return True, None
