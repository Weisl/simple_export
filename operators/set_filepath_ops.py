import bpy

from .fix_filename import SIMPLEEXPORT_OT_FixExportFilename
from .shared_properties import SharedPathProps, SharedFilenameProps
from ..core.export_path_func import get_export_folder_path, generate_base_name, generate_export_path, \
    assign_collection_exporter_path
from ..functions.collection_layer import set_active_layer_Collection
from ..functions.exporter_funcs import find_exporter
from ..functions.outliner_func import get_outliner_collections
from ..functions.vallidate_func import validate_collection


class SCENE_OT_SetExporterPathSelection(SharedPathProps, SharedFilenameProps, bpy.types.Operator):
    """Set export paths for selected collections."""
    bl_idname = "simple_export.set_export_paths"
    bl_label = "Set Export Path"
    bl_options = {'REGISTER', 'UNDO'}

    # Internal Properties
    outliner: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    individual_collection: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    collection_name: bpy.props.StringProperty(
        name="Collection Name", default='',
        description="Name of the collection to process", options={'HIDDEN'}
    )

    # Operator Properties are inherited from the parent classes

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        # Filepath settings
        from ..ui.shared_draw import draw_export_folderpath_properties, draw_export_filename_properties
        draw_export_filename_properties(box, self)

        box = layout.box()
        draw_export_folderpath_properties(box, self)

    def execute(self, context):
        results = []
        scene = context.scene

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
                # vallidation
                if not collection.simple_export_selected and not self.individual_collection:
                    continue
                if not collection.exporters:
                    continue
                collection = validate_collection(collection.name)
                if not collection:
                    continue

                # set exporter
                set_active_layer_Collection(collection.name)
                exporter = find_exporter(collection, scene.export_format)
                if not exporter:
                    continue

                collection_name = collection.name

                export_folder, is_relative_path = get_export_folder_path(self.export_folder_mode,
                                                                         self.folder_path_absolute,
                                                                         self.folder_path_relative,
                                                                         self.folder_path_search,
                                                                         self.folder_path_replace)

                # Simple check for empty paths
                if not export_folder:
                    results.append({'name': collection.name, 'success': False, 'filepath': '',
                                    'message': 'Export path is empty. Please specify a valid export folder.'})
                    continue

                # FILE: filename properties
                filename = generate_base_name(collection_name, self.filename_prefix, self.filename_suffix,
                                              self.filename_blend_prefix)

                # Generate final export path
                export_path = generate_export_path(export_folder, filename, scene.export_format,
                                                   is_relative_path=is_relative_path)

                try:
                    collection["prev_name"] = collection.name

                    # Assign path to exporter
                    success, msg = assign_collection_exporter_path(exporter, export_path,
                                                                   is_relative_path=is_relative_path)
                except Exception as e:
                    export_path = ''
                    success = False
                    msg = str(e)
                    print(e)

                finally:
                    results.append(
                        {'name': collection.name, 'success': success, 'filepath': export_path, 'message': msg})

            except Exception as e:
                results.append({'name': collection.name, 'success': False, 'filepath': '', 'message': str(e)})
                print(e)

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
