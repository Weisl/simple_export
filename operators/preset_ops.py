import bpy
import os

from .. import __package__ as base_package
from ..functions.exporter_funcs import find_exporter
from ..functions.outliner_func import get_outliner_collections
from ..functions.preset_func import assign_preset


class SIMPLEEXPORTER_OT_ApplyPresetSelection(bpy.types.Operator):
    """Operator to apply the preset to all collections"""
    bl_idname = "simple_export.assign_presets"
    bl_label = "Assign Presets"

    outliner: bpy.props.BoolProperty(default=False)
    individual_collection: bpy.props.BoolProperty(default=False)
    collection_name: bpy.props.StringProperty(name="Collection Name", default='',
                                              description="Name of the collection to process")

    def execute(self, context):
        results = []  # To store the renaming status of each collection
        prefs = context.preferences.addons[base_package].preferences
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

            # Get Export Collections
            # triggered from outliner
            if self.outliner:
                collection_list = get_outliner_collections(context)
            # triggered from the UI List
            elif self.individual_collection:  # Retrieve collection by name
                collection = bpy.data.collections.get(self.collection_name)
                collection_list = [collection] if collection else []
            # default
            else:
                collection_list = [
                    col for col in bpy.data.collections
                    if getattr(col, "simple_export_selected", False) and len(getattr(col, "exporters", [])) > 0
                ]

            if not collection_list:
                self.report({'WARNING'}, "No valid collections found for export.")
                return {'CANCELLED'}

            # Iterate over export collections
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
    SIMPLEEXPORTER_OT_ApplyPresetSelection,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
