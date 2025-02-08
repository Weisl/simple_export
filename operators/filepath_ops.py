import bpy
import os

from .. import __package__ as base_package
from ..core.export_path_func import generate_export_path, assign_exporter_path
from ..functions.collection_layer import set_active_layer_Collection
from ..functions.exporter_funcs import find_exporter
from ..functions.outliner_func import get_outliner_collections
from ..functions.vallidate_func import validate_collection


class SCENE_OT_SetExporterPathSelection(bpy.types.Operator):
    """
    Operator to set the exporter path for a collection based on the original and replacement paths defined in the scene properties.
    """
    bl_idname = "simple_export.set_export_paths"
    bl_label = "Set Export Path"
    bl_options = {'REGISTER', 'UNDO'}

    outliner: bpy.props.BoolProperty(default=False)
    individual_collection: bpy.props.BoolProperty(default=False)
    collection_name: bpy.props.StringProperty(name="Collection Name", default='',
                                              description="Name of the collection to process")

    def execute(self, context):
        results = []  # To store the renaming status of each collection
        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene
        settings_col = scene if scene.overwrite_collection_settings else prefs
        settings_filepath = scene if scene.overwrite_filepath_settings else prefs

        # Get Export Collections
        # triggered from outliner
        if self.outliner:
            collection_list = get_outliner_collections(context)
        #triggered from the UI List
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

        #Iterate over export collections
        for collection in collection_list:
            try:
                # return early
                if not collection.simple_export_selected or len(collection.exporters) == 0:
                    continue

                # Validate collection
                collection = validate_collection(collection.name)
                if not collection:
                    continue

                set_active_layer_Collection(collection.name)

                # Find and validate exporter
                exporter = find_exporter(collection, scene.export_format)

                if not exporter:
                    continue

                if settings_filepath.export_folder_mode == 'ABSOLUTE':
                    if not settings_filepath.custom_export_path:
                        raise ValueError("ERROR: Please specify a Custom Export Folder!")

                    export_dir = settings_filepath.custom_export_path
                else:
                    # Return if Blend File hasn't been saved
                    if not bpy.data.filepath:
                        raise ValueError("Save the Blend file before calling this operator.")

                    export_dir = os.path.dirname(bpy.data.filepath)

                # Path variables
                mirror_search_path = settings_filepath.mirror_search_path
                replacement_path = settings_filepath.replacement_path

                export_path = generate_export_path(collection.name, scene.export_format, export_dir, mirror_search_path,
                                                   replacement_path)
                success, msg = assign_exporter_path(exporter, export_path)
                results.append({'name': collection.name, 'success': success, 'filepath': export_path, 'message': msg})

            except Exception as e:
                # Handle per-collection errors
                results.append({'name': collection.name, 'success': False, 'filepath': '', 'message': str(e)})

        # Store results in WindowManager
        context.window_manager.assign_filepath_result_info = str(results)
        # Show results in the panel
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
