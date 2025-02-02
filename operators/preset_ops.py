import bpy
import os

from ..functions.exporter_funcs import find_exporter
from ..functions.outliner_func import get_outliner_collections
from ..functions.preset_func import assign_preset


class SIMPLEEXPORTER_PT_PresetResultsPanel(bpy.types.Panel):
    """Panel to display the results of applying the preset."""
    bl_idname = "SIMPLEEXPORTER_PT_PresetResultsPanel"
    bl_label = "Preset Application Results"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 30

    def draw(self, context):
        layout = self.layout
        layout.label(text="Assign Preset:")

        # Get results from Scene
        results_str = context.window_manager.assign_preset_info_data
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
            split = layout.split(factor=0.05)  # Split for each row
            col_icon = split.column()
            col_name = split.column()
            col_message = split.column()

            # Icon Column
            col_icon.label(icon='CHECKMARK' if result['success'] else 'CANCEL')

            # Collection Name Column
            collection_name = result['name']
            collection = bpy.data.collections[collection_name]
            color_tag = collection.color_tag
            icon = COLOR_TAG_ICONS.get(color_tag, 'NONE')
            col_name.label(text=result['name'], icon=icon)

            # Info Message Column
            col_message.label(text=result['message'])


class SIMPLEEXPORTER_OT_ApplyPreset(bpy.types.Operator):
    """Operator to apply the preset"""
    bl_idname = "simple_export.assign_preset"
    bl_label = "Assign Preset"

    collection_name: bpy.props.StringProperty()

    def execute(self, context):

        prefs = bpy.context.preferences.addons[__package__].preferences
        scene = context.scene

        collection = bpy.data.collections.get(self.collection_name)

        # Construct the property name dynamically
        export_format = scene.export_format.lower()
        prop_name = f"simple_export_preset_file_{export_format}"

        # Get preset path
        preset_settings = scene if scene.overwrite_preset_settings else prefs
        preset_path = getattr(preset_settings, prop_name, None)

        if not collection:
            self.report({'ERROR'}, f"Collection '{self.collection_name}' not found.")
            return {'CANCELLED'}

        if not preset_path:
            self.report({'ERROR'}, f"Select a preset to be applied.")
            return {'CANCELLED'}

        preset_name = os.path.basename(preset_path)
        exporter = find_exporter(collection, scene.export_format)

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

    outliner: bpy.props.BoolProperty()

    def execute(self, context):
        results = []  # To store the renaming status of each collection
        prefs = bpy.context.preferences.addons[__package__].preferences
        scene = context.scene

        # Construct the property name dynamically
        export_format = scene.export_format.lower()
        prop_name = f"simple_export_preset_file_{export_format}"

        # Get preset path
        preset_settings = scene if scene.overwrite_preset_settings else prefs
        preset_path = getattr(preset_settings, prop_name, None)

        try:
            # Validate preset path
            self.validate_preset_path(preset_path)

            collection_list = bpy.data.collections
            if self.outliner:
                collection_list = get_outliner_collections(context)

            for collection in collection_list:

                # return early
                if not collection.simple_export_selected or len(collection.exporters) == 0:
                    continue

                # Find and validate exporter
                exporter = find_exporter(collection, scene.export_format)

                if not exporter:
                    continue

                try:
                    # Process each collection
                    result = self.apply_preset_to_collections(collection, preset_path, exporter)
                    results.append(result)
                except Exception as e:
                    # Handle per-collection errors
                    results.append({'name': collection.name, 'success': False, 'message': str(e)})

        except Exception as e:
            # Handle global errors
            self.report({'ERROR'}, str(e))
            return {'CANCELLED'}

        # Store results in Scene
        context.window_manager.assign_preset_info_data = str(results)

        # Show results in the panel
        bpy.ops.wm.call_panel(name="SIMPLEEXPORTER_PT_PresetResultsPanel")
        return {'FINISHED'}

    def validate_preset_path(self, preset_path):
        """Ensure the preset path is valid."""
        if not preset_path:
            raise ValueError("Select a preset to be applied.")

    def apply_preset_to_collections(self, collection, preset_path, exporter):
        """Apply the preset to a single collection."""
        preset_name = os.path.basename(preset_path)

        # Apply preset
        success, msg = assign_preset(exporter, preset_path)
        if not success:
            raise ValueError(msg)

        # Add success result
        return {'name': collection.name, 'success': True, 'message': f"Applied preset '{preset_name}'."}


classes = (
    SIMPLEEXPORTER_PT_PresetResultsPanel,
    SIMPLEEXPORTER_OT_ApplyPreset,
    SIMPLEEXPORTER_OT_ApplyPresetSelection
)


def register():
    bpy.types.WindowManager.assign_preset_info_data = bpy.props.StringProperty(default="[]")

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    del bpy.types.Scene.assign_preset_info_data

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
