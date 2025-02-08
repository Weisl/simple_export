import os

import bpy

from .. import __package__ as base_package
from ..core.export_path_func import generate_export_path, assign_exporter_path
from ..functions.collection_layer import set_active_layer_Collection
from ..functions.exporter_funcs import find_exporter
from ..functions.outliner_func import get_outliner_collections
from ..functions.vallidate_func import validate_collection


class SCENE_OT_SetExporterPathSelection(bpy.types.Operator):
    """Set export paths for selected collections."""
    bl_idname = "simple_export.set_export_paths"
    bl_label = "Set Export Path"
    bl_options = {'REGISTER', 'UNDO'}

    outliner: bpy.props.BoolProperty(default=False)
    individual_collection: bpy.props.BoolProperty(default=False)
    collection_name: bpy.props.StringProperty(name="Collection Name", default='',
                                              description="Name of the collection to process")

    def execute(self, context):
        results = []
        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene
        settings_col = scene if scene.overwrite_collection_settings else prefs
        settings_filepath = scene if scene.overwrite_filepath_settings else prefs

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

        # Iterate over collections
        for collection in collection_list:
            try:
                if not collection.simple_export_selected or not collection.exporters:
                    continue

                collection = validate_collection(collection.name)
                if not collection:
                    continue

                set_active_layer_Collection(collection.name)

                # Find the appropriate exporter
                exporter = find_exporter(collection, scene.export_format)
                if not exporter:
                    continue

                # Determine filepath mode
                export_dir = None
                if settings_filepath.export_folder_mode == 'ABSOLUTE':
                    if not settings_filepath.custom_export_path:
                        raise ValueError("ERROR: Please specify a Custom Export Folder!")
                    export_dir = settings_filepath.custom_export_path
                    relative_mode = False

                elif settings_filepath.export_folder_mode == 'RELATIVE':
                    if not bpy.data.filepath:
                        raise ValueError("Save the Blend file before calling this operator.")
                    export_dir = settings_filepath.relative_export_path
                    relative_mode = True

                elif settings_filepath.export_folder_mode == 'MIRROR':
                    if not bpy.data.filepath:
                        raise ValueError("Save the Blend file before calling this operator.")
                    export_dir = os.path.dirname(bpy.data.filepath)  # Start with .blend file location
                    relative_mode = False  # Mirrored paths are not inherently relative

                # Path variables
                mirror_search_path = settings_filepath.mirror_search_path
                mirror_replacement_path = settings_filepath.mirror_replacement_path

                # Generate final export path
                export_path = generate_export_path(
                    collection.name, scene.export_format, export_dir,
                    mirror_search_path, mirror_replacement_path, relative_mode
                )

                # Assign path to exporter
                success, msg = assign_exporter_path(exporter, export_path, settings_filepath.export_folder_mode)
                results.append({'name': collection.name, 'success': success, 'filepath': export_path, 'message': msg})

            except Exception as e:
                results.append({'name': collection.name, 'success': False, 'filepath': '', 'message': str(e)})

        # Store results in WindowManager for UI display
        context.window_manager.assign_filepath_result_info = str(results)
        bpy.ops.wm.call_panel(name="SIMPLEEXPORTER_PT_FilePathResultsPanel")

        return {'FINISHED'}


classes = (
    SCENE_OT_SetExporterPathSelection,
)


# Register the scene property
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
