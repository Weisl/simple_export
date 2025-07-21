import bpy
import os

from .. import __package__ as base_package
from ..functions.collection_layer import set_active_layer_Collection
from ..functions.exporter_funcs import find_exporter
from ..functions.outliner_func import get_outliner_collections
from ..functions.preset_func import set_preset
from ..functions.vallidate_func import validate_collection


class SIMPLEEXPORTER_OT_ApplyPresetSelection(bpy.types.Operator):
    """Operator to apply the preset to all collections"""
    bl_idname = "simple_export.set_presets"
    bl_label = "Assign Presets"

    outliner: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    individual_collection: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    collection_name: bpy.props.StringProperty(name="Collection Name", default='',
                                              description="Name of the collection to process", options={'HIDDEN'})

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
                exporter = find_exporter(collection, scene.export_format)
                if not exporter:
                    continue

                result = self.apply_preset_to_collections(collection, preset_path, exporter)
                results.append(result)

            except Exception as e:
                # Handle per-collection errors
                results.append({'name': collection.name, 'success': False, 'message': str(e)})

        # Store results in Scene
        context.window_manager.set_preset_info_data = str(results)
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
        success, msg = set_preset(exporter, preset_path)
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
