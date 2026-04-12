import os

import bpy

from .shared_properties import SharedPresetAssignmentProps, SharedFormatProps
from ..functions.collection_layer import set_active_layer_Collection
from ..functions.exporter_funcs import find_exporter
from ..functions.outliner_func import get_outliner_collections
from ..functions.preset_func import assign_preset
from ..functions.vallidate_func import validate_collection


class SIMPLEEXPORTER_OT_ApplyPresetSelection(bpy.types.Operator, SharedPresetAssignmentProps, SharedFormatProps):
    """Operator to apply the preset to all collections"""
    bl_idname = "simple_export.assign_presets"
    bl_label = "Assign Export Format Presets"
    bl_description = "Assign presets to selected collections based on the current export format."
    bl_options = {'REGISTER', 'UNDO'}

    outliner: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    individual_collection: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    collection_name: bpy.props.StringProperty(name="Collection Name", default='',
                                              description="Name of the collection to process", options={'HIDDEN'})

    def draw(self, context):
        """Draw the UI for the operator."""
        layout = self.layout
        from ..ui.shared_draw import draw_export_preset_properties
        draw_export_preset_properties(layout, self)

    def execute(self, context):
        results = []  # To store the renaming status of each collection

        # Construct the property name dynamically
        export_format = self.export_format
        prop_name = f"simple_export_preset_file_{export_format.lower()}"

        preset_settings = self
        # Get preset path
        preset_path = getattr(preset_settings, prop_name, None)

        # Get Export Collections
        if self.outliner:
            collection_list = get_outliner_collections(context)
        elif self.individual_collection:
            collection = bpy.data.collections.get(self.collection_name)
            collection_list = [collection] if collection else []
        else:
            collection_list = [
                col for col in bpy.data.collections
                if getattr(col, "simple_export_selected", False) and len(getattr(col, "exporters", [])) > 0
            ]

        if not collection_list:
            self.report({'WARNING'}, "No valid collections found for export.")
            return {'CANCELLED'}

        # Validate preset path
        self.validate_preset_path(preset_path)

        # Iterate over export collections
        for collection in collection_list:
            try:

                if not collection.simple_export_selected and not self.individual_collection:  # Don't check selected for individual collection
                    continue

                if not collection.exporters:
                    continue

                collection = validate_collection(collection.name)
                if not collection:
                    continue

                set_active_layer_Collection(collection.name)

                # Find the appropriate exporter
                exporter = find_exporter(collection, format_filter= export_format)
                if not exporter:
                    continue

                result = self.apply_preset_to_collections(collection, preset_path, exporter)
                results.append(result)

            except Exception as e:
                # Handle per-collection errors
                results.append({'name': collection.name, 'success': False, 'message': str(e)})

        # Show result popup when started from Outliner
        if self.outliner:
            # Store results in Scene
            context.window_manager.assign_preset_info_data = str(results)
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

        collection.last_preset_name = os.path.splitext(preset_name)[0]

        # Add success result
        return {'name': collection.name, 'success': True, 'message': f"Applied preset '{preset_name}'."}


classes = (
    SIMPLEEXPORTER_OT_ApplyPresetSelection,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
