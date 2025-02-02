import bpy
import os

from extensions.simple_export.core.export_path_func import generate_export_path, assign_exporter_path
from ..functions.collection_layer import set_active_layer_Collection
from ..functions.exporter_funcs import find_exporter
from ..functions.outliner_func import get_outliner_collections
from ..functions.vallidate_func import validate_collection


class SCENE_OT_SetExporterPath(bpy.types.Operator):
    """
    Operator to set the exporter path for a collection based on the original and replacement paths defined in the scene properties.
    """
    bl_idname = "scene.set_export_path"
    bl_label = "Set Export Path"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)

        prefs = bpy.context.preferences.addons[__package__].preferences
        scene = context.scene
        settings_col = scene if scene.overwrite_collection_settings else prefs
        settings_filepath = scene if scene.overwrite_filepath_settings else prefs

        if settings_filepath.use_custom_export_folder:
            # Return if Custom Export Path is invalid
            if not settings_filepath.custom_export_path:
                self.report({'ERROR'}, f"Please specify a Custom Export Folder!")
                return {'CANCELLED'}
            export_dir = settings_filepath.custom_export_path

        if not settings_filepath.use_custom_export_folder:
            blend_filepath = bpy.data.filepath
            # Return if Blend File hasn't been saved
            if not blend_filepath:
                self.report({'ERROR'}, f"Save the Blend file before calling this operator.")
                return {'CANCELLED'}
            export_dir = os.path.dirname(blend_filepath)

        # Return if collection not found
        if not collection:
            self.report({'ERROR'}, f"Collection '{self.collection_name}' not found.")
            return {'CANCELLED'}

        # Path variables
        search_path = settings_filepath.search_path
        replacement_path = settings_filepath.replacement_path

        # Add custom exporter
        exporter = find_exporter(collection, scene.export_format)

        # Return
        if not exporter:
            self.report({'ERROR'}, f"Could not add exporter to collection '{collection.name}'.")
            return {'CANCELLED'}

        # Set export Path
        export_format = scene.export_format
        export_path = generate_export_path(collection.name, export_format, export_dir, search_path, replacement_path)
        success, msg = assign_exporter_path(exporter, export_path)

        self.report({'INFO'}, f"Export path set to {export_path}")
        return {'FINISHED'}

    def get_custom_exporter_for_collection(self, collection_name, exporter_name):
        """
        Retrieve the custom exporter for a given collection.

        Args:
            collection_name (str): The name of the collection.
            exporter_name (str): The name of the exporter.

        Returns:
            bpy.types.PropertyGroup or None: The exporter if found, otherwise None.
        """
        collection = bpy.data.collections.get(collection_name)
        if not collection:
            return None

        for exporter in collection.exporters:
            if exporter.name == exporter_name:
                return exporter

        return None


class SCENE_OT_SetExporterPathSelection(bpy.types.Operator):
    """
    Operator to set the exporter path for a collection based on the original and replacement paths defined in the scene properties.
    """
    bl_idname = "scene.set_export_path_selection"
    bl_label = "Set Export Path"
    bl_options = {'REGISTER', 'UNDO'}

    outliner: bpy.props.BoolProperty()

    def execute(self, context):
        results = []  # To store the renaming status of each collection
        prefs = bpy.context.preferences.addons[__package__].preferences
        scene = context.scene
        settings_col = scene if scene.overwrite_collection_settings else prefs
        settings_filepath = scene if scene.overwrite_filepath_settings else prefs

        collection_list = bpy.data.collections
        if self.outliner:
            collection_list = get_outliner_collections(context)

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

                if settings_filepath.use_custom_export_folder:
                    if not settings_filepath.custom_export_path:
                        raise ValueError("ERROR: Please specify a Custom Export Folder!")

                    export_dir = settings_filepath.custom_export_path
                else:
                    # Return if Blend File hasn't been saved
                    if not bpy.data.filepath:
                        raise ValueError("Save the Blend file before calling this operator.")

                    export_dir = os.path.dirname(bpy.data.filepath)

                # Path variables
                search_path = settings_filepath.search_path
                replacement_path = settings_filepath.replacement_path

                export_path = generate_export_path(collection.name, scene.export_format, export_dir, search_path,
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
    SCENE_OT_SetExporterPath,
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
