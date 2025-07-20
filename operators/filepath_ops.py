import bpy
import os

from .. import __package__ as base_package
from ..core.export_path_func import assign_export_path_to_exporter
from ..functions.collection_layer import set_active_layer_Collection
from ..functions.create_collection_func import generate_base_name
from ..functions.exporter_funcs import find_exporter
from ..functions.outliner_func import get_outliner_collections
from ..functions.vallidate_func import validate_collection
from .create_exporter import SharedPathProperties, SharedFilenameProperties


class SIMPLEEXPORT_OT_FixExportFilename(SharedPathProperties, SharedFilenameProperties, bpy.types.Operator):
    """Fix the export filename for a collection."""
    bl_idname = "simple_export.fix_export_filename"
    bl_label = "Fix Export Filename"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty(
        name="Collection Name",
        description="Name of the collection to fix",
        default=""
    )

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if not collection or not collection.exporters:
            return {'CANCELLED'}

        scene = context.scene
        exporter = find_exporter(collection, scene.export_format)
        if not exporter:
            return {'CANCELLED'}

        export_path = exporter.export_properties.filepath
        export_dir = os.path.dirname(export_path)
        _, ext = os.path.splitext(export_path)

        base_name = generate_base_name(collection.name, self.filename_custom_prefix,
                                       self.filename_custom_suffix,
                                       self.filename_file_name_prefix)

        new_export_path = os.path.join(export_dir, f"{base_name}{ext}")
        exporter.export_properties.filepath = new_export_path
        collection["prev_name"] = collection.name

        return {'FINISHED'}


class SCENE_OT_SetExporterPathSelection(SharedPathProperties, SharedFilenameProperties, bpy.types.Operator):
    """Set export paths for selected collections."""
    bl_idname = "simple_export.set_export_paths"
    bl_label = "Set Export Path"
    bl_options = {'REGISTER', 'UNDO'}

    outliner: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    individual_collection: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    collection_name: bpy.props.StringProperty(
        name="Collection Name", default='',
        description="Name of the collection to process", options={'HIDDEN'}
    )

    def draw(self, context):
        layout = self.layout
        
        # Filepath settings
        box = layout.box()
        box.label(text="File Path Settings")
        from ..ui.export_panels import draw_operator_filepath_settings
        draw_operator_filepath_settings(box, self)
        
        # Filename settings
        box = layout.box()
        box.label(text="File Name Settings")
        box.prop(self, "filename_custom_prefix")
        box.prop(self, "filename_custom_suffix")
        box.prop(self, "filename_file_name_prefix")

    def execute(self, context):
        results = []
        scene = context.scene
        
        # Create mock objects that mimic the settings objects
        class MockFilepathSettings:
            def __init__(self, props):
                self.export_folder_mode = props['export_folder_mode']
                self.absolute_export_path = props['absolute_export_path']
                self.relative_export_path = props['relative_export_path']
                self.mirror_search_path = props['mirror_search_path']
                self.mirror_replacement_path = props['mirror_replacement_path']
        
        class MockFilenameSettings:
            def __init__(self, props):
                self.filename_custom_prefix = props['filename_custom_prefix']
                self.filename_custom_suffix = props['filename_custom_suffix']
                self.filename_file_name_prefix = props['filename_file_name_prefix']
        
        # Create mock settings objects from operator properties
        filepath_props = {
            'export_folder_mode': self.export_folder_mode,
            'absolute_export_path': self.absolute_export_path,
            'relative_export_path': self.relative_export_path,
            'mirror_search_path': self.mirror_search_path,
            'mirror_replacement_path': self.mirror_replacement_path,
        }
        
        filename_props = {
            'filename_custom_prefix': self.filename_custom_prefix,
            'filename_custom_suffix': self.filename_custom_suffix,
            'filename_file_name_prefix': self.filename_file_name_prefix,
        }
        
        settings_filepath = MockFilepathSettings(filepath_props)
        settings_filename = MockFilenameSettings(filename_props)

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
                if not collection.simple_export_selected and not self.individual_collection:
                    continue
                if not collection.exporters:
                    continue
                collection = validate_collection(collection.name)
                if not collection:
                    continue
                set_active_layer_Collection(collection.name)
                exporter = find_exporter(collection, scene.export_format)
                if not exporter:
                    continue
                # Assign export path using the extracted function
                success, export_path, msg = assign_export_path_to_exporter(
                    collection, exporter, scene, settings_filepath, settings_filename
                )
                results.append({'name': collection.name, 'success': success, 'filepath': export_path, 'message': msg})
            except Exception as e:
                results.append({'name': collection.name, 'success': False, 'filepath': '', 'message': str(e)})

        # Store results in WindowManager for UI display
        context.window_manager.assign_filepath_result_info = str(results)
        bpy.ops.wm.call_panel(name="SIMPLEEXPORTER_PT_FilePathResultsPanel")

        return {'FINISHED'}


classes = (
    SIMPLEEXPORT_OT_FixExportFilename,
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
