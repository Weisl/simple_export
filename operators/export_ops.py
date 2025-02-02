import bpy

from .. import __package__ as base_package
from ..functions.collection_layer import set_active_layer_Collection
from ..functions.collection_offset import apply_collection_offset
from ..functions.collection_offset import temporarily_disable_offset_handler
from ..functions.exporter_funcs import find_exporter, get_exporter_id, add_extension
from ..functions.outliner_func import get_outliner_collections
from ..functions.path_utils import clean_relative_path
from ..functions.vallidate_func import validate_collection, post_export_checks, pre_export_checks


def call_export_popup(export_results, context):
    """Handle cancellation with results."""
    # Store results in WindowManager
    context.window_manager.export_data_info = str(export_results)

    bpy.ops.wm.call_panel(name="SIMPLEEXPORTER_PT_ExportResultsPanel")
    return {'CANCELLED'}


class SCENE_OT_ExportCollection(bpy.types.Operator):
    """
    Operator to export a single collection with post-export validations and results popup.
    """

    bl_idname = "simple_export.export_collection"
    bl_label = "Export Collection"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        export_results = []
        temporarily_disable_offset_handler()
        success = False

        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene
        settings_col = scene if scene.overwrite_collection_settings else prefs
        settings_filepath = scene if scene.overwrite_filepath_settings else prefs

        export_path = ''

        try:
            # Validate collection
            collection = validate_collection(self.collection_name)
            set_active_layer_Collection(collection.name)

            # Find and validate exporter
            exporter = find_exporter(collection, scene.export_format)
            exporter_id = get_exporter_id(self, collection, exporter)

            if not exporter.export_properties.filepath:
                raise ValueError(f"Please specify a export path for {collection.name}.")

            # Pre-export  path adjustments
            export_path = add_extension(exporter.export_properties.filepath, scene.export_format)
            export_path = clean_relative_path(export_path)

            # Apply updates to exporter  (unfortunately necessary for the add extension to work)
            exporter.export_properties.filepath = export_path

            # Overwrite settings:
            # Having use_selection causes unpredictable behavior and is not exposed to the UI.
            exporter.export_properties.use_selection = False

            print('EXPORT PATH: ' + str(export_path))

            file_exists_before, file_timestamp_before = pre_export_checks(export_path)

            # Apply instance offset if enabled
            if scene.move_by_collection_offset:
                apply_collection_offset(collection)

            # Perform the export
            bpy.ops.collection.exporter_export(index=exporter_id)

            # Post-export validation
            success, message = post_export_checks(export_path, file_exists_before, file_timestamp_before)
            export_results.append(
                {'name': collection.name, 'success': success, 'filepath': export_path, 'message': message})

        except Exception as e:
            # Handle errors in one place
            export_path = export_path or ''

            export_results.append(
                {'name': self.collection_name or "Unknown Collection", 'success': False, 'filepath': export_path,
                 'message': str(e)})

        finally:
            if scene.move_by_collection_offset:
                # Revert instance offset and show results
                apply_collection_offset(collection, inverse=True)

        if success:
            self.report({'INFO'}, f"Export Sucessful")

            # Always show export infos
            if not prefs.report_errors_only:
                call_export_popup(export_results, context)

            return {'FINISHED'}

        else:
            self.report({'ERROR'}, f"Export failed")
            call_export_popup(export_results, context)
            return {'CANCELLED'}


# Operator to export selected collections
class SCENE_OT_ExportCollectionsSelection(bpy.types.Operator):
    bl_idname = "simple_export.export_selected_collections"
    bl_label = "Export Selected"
    bl_options = {'REGISTER', 'UNDO'}

    outliner: bpy.props.BoolProperty()

    def execute(self, context):
        export_results = []
        export_collections = []
        temporarily_disable_offset_handler()
        error_count = 0

        prefs = context.preferences.addons[base_package].preferences
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

                exporter_id = get_exporter_id(self, collection, exporter)

                # Pre-export checks
                if not exporter.export_properties.filepath:
                    raise ValueError(f"Please specify a export path for {collection.name}.")

                export_path = add_extension(exporter.export_properties.filepath, scene.export_format)
                export_path = clean_relative_path(export_path)

                # Apply updates to exporter  (unfortunately necessary for the add extension to work)
                exporter.export_properties.filepath = export_path

                # Overwrite settings:
                # Having use_selection causes unpredictable behavior and is not exposed to the UI.
                exporter.export_properties.use_selection = False

                file_exists_before, file_timestamp_before = pre_export_checks(export_path)

                # Apply instance offset if enabled
                if scene.move_by_collection_offset:
                    apply_collection_offset(collection)

                export_collections.append(collection)

                # Perform the export
                bpy.ops.collection.exporter_export(index=exporter_id)

                # Post-export validation
                success, message = post_export_checks(export_path, file_exists_before, file_timestamp_before)
                export_results.append(
                    {'name': collection.name, 'success': success, 'filepath': export_path, 'message': message})
                if not success:
                    error_count += 1


            except Exception as e:
                # Handle errors in one place
                export_results.append(
                    {'name': collection.name or "Unknown Collection", 'success': False, 'filepath': export_path,
                     'message': str(e)})

            finally:
                if scene.move_by_collection_offset:
                    apply_collection_offset(collection, inverse=True)

        if error_count == 0:
            self.report({'INFO'}, f"Export Sucessful")
            # Always show export infos
            if not prefs.report_errors_only:
                call_export_popup(export_results, context)

            return {'FINISHED'}

        else:
            self.report({'WARNING'}, f"Export with Errors: See Result windows or console for further information.")
            call_export_popup(export_results, context)
            return {'CANCELLED'}


classes = (
    SCENE_OT_ExportCollection,
    SCENE_OT_ExportCollectionsSelection,
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
