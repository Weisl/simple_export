import bpy
import os

from .. import __package__ as base_package
from ..functions.collection_layer import set_active_layer_Collection
from ..functions.collection_offset import apply_collection_offset
from ..functions.pre_export_ops import (
    apply_triangulate_modifiers, remove_triangulate_modifiers,
    apply_scale_for_export, restore_scale_after_export,
    apply_rotation_for_export, restore_rotation_after_export,
    apply_transform_for_export, restore_transform_after_export,
    apply_pre_rotation, restore_pre_rotation,
)
from ..functions.exporter_funcs import find_exporter, get_exporter_id, add_extension
from ..functions.outliner_func import get_outliner_collections
from ..functions.path_utils import clean_relative_path, ensure_export_folder_exists, make_folder_path_absolute
from ..functions.vallidate_func import validate_collection, post_export_checks, pre_export_checks, check_collection_warnings
from ..ui.uilist import collection_passes_uilist_filters


def call_export_popup(export_results, context):
    """Handle cancellation with results."""
    # Store results in WindowManager
    context.window_manager.export_data_info = str(export_results)

    bpy.ops.wm.call_panel(name="SIMPLEEXPORTER_PT_ExportResultsPanel")
    return {'CANCELLED'}


# Operator to export selected collections
class SCENE_OT_ExportCollectionsSelection(bpy.types.Operator):
    bl_idname = "simple_export.export_collections"
    bl_label = "Export Selected"
    bl_description = "Export selected collections with their exporters and settings."
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    # Internal Properties   
    outliner: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    individual_collection: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    collection_name: bpy.props.StringProperty(name="Collection Name", default='',
                                              description="Name of the collection to process", options={'HIDDEN'})
    # Todo: Overwrite pre export settings like move_by_collection_offset

    def execute(self, context):
        export_results = []
        export_collections = []

        error_count = 0
        success_count = 0
        offset = (0.0, 0.0, 0.0)

        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene

        # Get Export Collections
        if self.outliner:
            collection_list = get_outliner_collections(context)
        elif self.individual_collection:  # Retrieve collection by name
            collection = bpy.data.collections.get(self.collection_name)
            collection_list = [collection] if collection else []
        else:
            collection_list = [
                col for col in bpy.data.collections
                if getattr(col, "simple_export_selected", False)
                and collection_passes_uilist_filters(col, scene)
            ]

        if not collection_list:
            self.report({'WARNING'}, "No valid collections found for export.")
            return {'CANCELLED'}

        # --- Pre-pass: detect duplicate output paths ---
        # Resolve each collection's export path without modifying exporter state,
        # then flag every collection involved in a conflict so nothing overwrites silently.
        _path_to_col_names = {}  # abs_path -> [collection_name, ...]
        for _col in collection_list:
            if not _col.exporters:
                continue
            _exp = find_exporter(_col)
            if not _exp:
                continue
            _raw_fp = _exp.export_properties.filepath
            if not _raw_fp or (not bpy.data.filepath and _raw_fp.startswith("//")):
                continue
            try:
                _abs = make_folder_path_absolute(clean_relative_path(add_extension(_exp)))
            except Exception:
                continue
            _path_to_col_names.setdefault(_abs, []).append(_col.name)

        # Build per-collection error messages for every path that is shared
        _skip_duplicates = {}  # col_name -> error message string
        for _abs_path, _col_names in _path_to_col_names.items():
            if len(_col_names) > 1:
                _filename = os.path.basename(_abs_path)
                for _col_name in _col_names:
                    _others = ', '.join(f"'{n}'" for n in _col_names if n != _col_name)
                    _skip_duplicates[_col_name] = (
                        f"Duplicate output path '{_filename}' — also targeted by: {_others}. "
                        "Assign unique paths before exporting."
                    )

        # Emit error results for all duplicates up front so they appear in the popup
        for _col_name, _dup_msg in _skip_duplicates.items():
            export_results.append({
                'name': _col_name, 'success': False, 'filepath': '',
                'message': _dup_msg, 'warnings': [],
            })
            _dup_col = bpy.data.collections.get(_col_name)
            if _dup_col:
                _dup_col.last_export_failed = True
            error_count += 1

        total = len(collection_list)
        wm = context.window_manager
        wm.progress_begin(0, total)

        # Iterate over export collections
        for i, collection in enumerate(collection_list):
            wm.progress_update(i)
            context.workspace.status_text_set(f"Exporting {i + 1}/{total}: {collection.name}")
            # Declare backup state before try so finally block can always access them
            scale_backup = {}
            rotation_backup = {}
            transform_backup = {}
            triangulate_backup = {}
            pre_rotate_backup = {}
            ops = None  # per-collection pre-export ops; set inside try after validation

            try:
                # Skip collections already flagged by the duplicate-path pre-pass
                if collection.name in _skip_duplicates:
                    continue

                if not collection.exporters:
                    continue

                collection = validate_collection(collection.name)
                if not collection:
                    continue

                if not collection.objects:
                    export_results.append(
                        {'name': collection.name, 'success': False, 'filepath': '',
                         'message': "Collection is empty. Nothing to export.", 'warnings': []})
                    collection.last_export_failed = True
                    error_count += 1
                    continue

                set_active_layer_Collection(collection.name)

                # Find and validate exporter
                exporter = find_exporter(collection)

                if not exporter:
                    continue

                exporter_id = get_exporter_id(self, collection, exporter)

                # Pre-export checks
                raw_filepath = exporter.export_properties.filepath
                if not raw_filepath:
                    raise ValueError(f"No export path set for '{collection.name}'. Please assign one before exporting.")

                # Catch relative paths when blend file is not saved
                if not bpy.data.filepath and raw_filepath.startswith("//"):
                    raise ValueError(
                        f"'{collection.name}' uses a relative export path but the .blend file has not been saved. "
                        "Save the .blend file first, or switch to an absolute export path."
                    )

                # TODO: Reaply extension based on exporter type
                export_path = add_extension(exporter)

                # Apply updates to exporter  (unfortunately necessary for the add extension to work)
                exporter.export_properties.filepath = export_path

                export_path = clean_relative_path(export_path)

                folder_ok, folder_msg = ensure_export_folder_exists(export_path)
                if not folder_ok:
                    raise ValueError(folder_msg)

                # Non-blocking pre-export warnings (hidden objects, missing libraries, textures…)
                pre_export_warnings = check_collection_warnings(collection, exporter)

                # Overwrite settings:
                # Having use_selection causes unpredictable behavior and is not exposed to the UI.
                if hasattr(exporter.export_properties, "use_selection"):
                    exporter.export_properties.use_selection = False

                file_exists_before, file_timestamp_before = pre_export_checks(export_path)

                # Per-collection pre-export operations
                ops = collection.pre_export_ops

                # Apply transforms (apply_transform subsumes scale+rotation)
                if ops.apply_transform_before_export:
                    transform_backup = apply_transform_for_export(collection)
                else:
                    if ops.apply_scale_before_export:
                        scale_backup = apply_scale_for_export(collection)
                    if ops.apply_rotation_before_export:
                        rotation_backup = apply_rotation_for_export(collection)

                # Triangulate (order-independent relative to transform baking)
                if ops.triangulate_before_export:
                    triangulate_backup = apply_triangulate_modifiers(collection, ops.triangulate_keep_normals)

                # Apply collection offset after transform baking
                if ops.move_by_collection_offset:
                    offset = collection.instance_offset.copy()
                    apply_collection_offset(collection, offset)

                # Pre-rotate last (rotation offset over final position)
                if ops.pre_rotate_objects:
                    pre_rotate_backup = apply_pre_rotation(collection, ops.pre_rotate_euler)

                export_collections.append(collection)

                # Bail out before calling the exporter if the target file is read-only,
                # so Blender's internal error popup is never triggered.
                # Use make_folder_path_absolute because clean_relative_path may leave
                # Blender-relative "//" prefixes that os.path.exists cannot resolve.
                _abs_export_path = make_folder_path_absolute(export_path)
                if os.path.exists(_abs_export_path) and not os.access(_abs_export_path, os.W_OK):
                    raise PermissionError(f"Export file is read-only: '{_abs_export_path}'.")

                # Perform the export
                bpy.ops.collection.exporter_export(index=exporter_id)

                # Post-export validation
                success, message = post_export_checks(export_path, file_exists_before, file_timestamp_before)
                export_results.append({
                    'name': collection.name, 'success': success, 'filepath': export_path,
                    'message': message, 'warnings': pre_export_warnings,
                })
                collection.last_export_failed = not success
                if not success:
                    error_count += 1
                else:
                    success_count += 1


            except Exception as e:
                # Handle errors in one place
                export_results.append({
                    'name': collection.name or "Unknown Collection", 'success': False,
                    'filepath': '', 'message': str(e), 'warnings': [],
                })
                collection.last_export_failed = True
                error_count += 1

            finally:
                # Restore in reverse order of application (ops may be None if we continued early)
                if ops and collection:
                    if ops.pre_rotate_objects:
                        restore_pre_rotation(collection, pre_rotate_backup)
                    if ops.move_by_collection_offset:
                        apply_collection_offset(collection, offset, inverse=True)
                    if ops.triangulate_before_export:
                        remove_triangulate_modifiers(collection, triangulate_backup)
                    if ops.apply_transform_before_export:
                        restore_transform_after_export(collection, transform_backup)
                    else:
                        if ops.apply_rotation_before_export:
                            restore_rotation_after_export(collection, rotation_backup)
                        if ops.apply_scale_before_export:
                            restore_scale_after_export(collection, scale_backup)

        wm.progress_end()
        context.workspace.status_text_set(None)

        if error_count == 0:
            self.report({'INFO'}, f"Export Sucessful")
            # Always show export infos
            if not prefs.report_errors_only:
                call_export_popup(export_results, context)

            return {'FINISHED'}
        elif success_count > 0:
            call_export_popup(export_results, context)
            return {'CANCELLED'}
        else:
            call_export_popup(export_results, context)
            return {'CANCELLED'}


classes = (
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
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
