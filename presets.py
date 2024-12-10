import os

import bpy

from .operators import find_exporter


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
        if prop_name == 'filepath':
            continue

        try:
            if hasattr(exporter.export_properties, prop_name):
                setattr(exporter.export_properties, prop_name, prop_value)
            else:
                print(f"Exporter property '{prop_name}' not found.")
        except Exception as e:
            print(f"Error setting property '{prop_name}': {e}")


# TODO: This should work based on the exporter not the collection
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


class SIMPLEEXPORTER_PT_ResultsPanel(bpy.types.Panel):
    """Panel to display the results of applying the preset."""
    bl_idname = "SIMPLEEXPORTER_PT_ResultsPanel"
    bl_label = "Preset Application Results"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 30


    def draw(self, context):
        layout = self.layout
        layout.label(text="Results:")

        # Get results from WindowManager
        results_str = context.window_manager.result_data
        results = eval(results_str) if results_str else []  # Parse results string into a list

        # Header row with column titles
        split = layout.split(factor=0.1)
        col_icon = split.column()  # Icon column
        col_name = split.column()  # Collection name column
        col_message = split.column()  # Info message column

        row = layout.row()
        col_icon.label(text="")
        col_name.label(text="Collection")
        col_message.label(text="Info")

        # Iterate over results and populate the table
        for result in results:
            split = layout.split(factor=0.1)  # Split for each row
            col_icon = split.column()
            col_name = split.column()
            col_message = split.column()

            # Icon Column
            col_icon.label(icon='CHECKMARK' if result['success'] else 'CANCEL')

            # Collection Name Column
            col_name.label(text=result['name'])

            # Info Message Column
            col_message.label(text=result['message'])


class SIMPLEEXPORTER_OT_ApplyPreset(bpy.types.Operator):
    """Operator to apply the preset"""
    bl_idname = "simple_export.assign_preset"
    bl_label = "Assign Preset"

    collection_name: bpy.props.StringProperty()

    def execute(self, context):

        collection = bpy.data.collections.get(self.collection_name)
        props = context.scene.simple_export_props
        preset_path = props.simple_export_preset_file

        if not collection:
            self.report({'ERROR'}, f"Collection '{self.collection_name}' not found.")
            return {'CANCELLED'}

        if not preset_path:
            self.report({'ERROR'}, f"Select a preset to be applied.")
            return {'CANCELLED'}

        preset_name = os.path.basename(preset_path)
        exporter = find_exporter(collection, props.export_format)

        suceess, msg = assign_preset(exporter, preset_path)

        if not suceess:
            self.report({'ERROR'}, "No exporters found in the current collection.")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Applied preset '{preset_name}' to {self.collection_name}.")
        return {'FINISHED'}


class SIMPLEEXPORTER_OT_ApplyPresetSelection(bpy.types.Operator):
    """Operator to apply the preset to all collections"""
    bl_idname = "simple_export.assign_preset_selection"
    bl_label = "Assign Presets"


    def execute(self, context):
        results = []  # To store the renaming status of each collection
        props = context.scene.simple_export_props
        preset_path = props.simple_export_preset_file

        try:
            # Validate preset path
            self.validate_preset_path(preset_path)

            # Iterate through all collections and apply preset
            for collection in bpy.data.collections:

                # return early
                if not collection.simple_export_selected or len(collection.exporters) == 0:
                    continue

                try:
                    # Process each collection
                    self.apply_preset_to_collection(collection, preset_path, props.export_format, results)
                except Exception as e:
                    # Handle per-collection errors
                    results.append({'name': collection.name, 'success': False, 'message': str(e)})

        except Exception as e:
            # Handle global errors
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        # Store results in WindowManager
        context.window_manager.result_data = str(results)

        # Show results in the panel
        bpy.ops.wm.call_panel(name="SIMPLEEXPORTER_PT_ResultsPanel")
        return {'FINISHED'}

    def validate_preset_path(self, preset_path):
        """Ensure the preset path is valid."""
        if not preset_path:
            raise ValueError("Select a preset to be applied.")

    def apply_preset_to_collection(self, collection, preset_path, export_format, results):
        """Apply the preset to a single collection."""
        preset_name = os.path.basename(preset_path)

        # Find exporter
        exporter = find_exporter(collection, export_format)
        if not exporter:
            raise ValueError("No exporters found in the current collection.")

        # Apply preset
        success, msg = assign_preset(exporter, preset_path)
        if not success:
            raise ValueError(msg)

        # Add success result
        results.append({'name': collection.name, 'success': True, 'message': f"Applied preset '{preset_name}'."})

classes = (
    SIMPLEEXPORTER_PT_ResultsPanel,
    SIMPLEEXPORTER_OT_ApplyPreset,
    SIMPLEEXPORTER_OT_ApplyPresetSelection
)


def register():
    bpy.types.WindowManager.result_data = bpy.props.StringProperty(default="[]")

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    del bpy.types.WindowManager.result_data

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
