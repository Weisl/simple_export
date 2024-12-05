import os

import bpy


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


def apply_preset_to_exporter(properties, exporter):
    """Apply parsed properties to the exporter."""
    for prop_name, prop_value in properties.items():
        try:
            if hasattr(exporter.export_properties, prop_name):
                setattr(exporter.export_properties, prop_name, prop_value)
                print(f"Applied {prop_name} = {prop_value}")
            else:
                print(f"Exporter property '{prop_name}' not found.")
        except Exception as e:
            print(f"Error setting property '{prop_name}': {e}")


class SIMPLEEXPORTER_OT_ApplyPreset(bpy.types.Operator):
    """Operator to apply the preset"""
    bl_idname = "simple_export.apply_preset"
    bl_label = "Apply Preset"

    collection_name: bpy.props.StringProperty()

    def execute(self, context):

        collection = bpy.data.collections.get(self.collection_name)
        props = context.scene.simple_export_props
        # I need to force it to be a raw string to work with paths
        preset_path = props.simple_export_preset_file

        if not collection:
            self.report({'ERROR'}, f"Collection '{self.collection_name}' not found.")
            return {'CANCELLED'}

        if not preset_path:
            self.report({'ERROR'}, f"Preset path {props.preset_path}' not found.")
            return {'CANCELLED'}


        # Ensure the collection has exporters
        if hasattr(collection, "exporters") and len(collection.exporters) > 0:
            exporter = collection.exporters[0]

            # Parse the preset file
            preset_properties = parse_preset_file(preset_path)

            # Apply the properties to the exporter
            apply_preset_to_exporter(preset_properties, exporter)

            preset_name = os.path.basename(preset_path)
            self.report({'INFO'}, f"Applied preset '{preset_name}' to {self.collection_name}.")

        else:
            self.report({'ERROR'}, "No exporters found in the current collection.")
            return {'CANCELLED'}

        return {'FINISHED'}


classes = (
    SIMPLEEXPORTER_OT_ApplyPreset,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
