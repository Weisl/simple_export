import os

import bpy

from .shared_properties import SharedPathProps, SharedFilenameProps
from ..core.export_path_func import get_export_folder_path, generate_base_name, generate_export_path, \
    assign_collection_exporter_path
from ..functions.collection_layer import set_active_layer_Collection
from ..functions.exporter_funcs import find_exporter
from ..core.export_formats import ExportFormats
from ..functions.outliner_func import get_outliner_collections
from ..functions.vallidate_func import validate_collection

_PATH_PROPS = [
    'export_folder_mode', 'folder_path_absolute', 'folder_path_relative',
    'folder_path_search', 'folder_path_replace',
    'filename_prefix', 'filename_suffix', 'filename_blend_prefix',
]


class SCENE_OT_SetExporterPathSelection(SharedPathProps, SharedFilenameProps, bpy.types.Operator):
    """Assign Exporter Pathss for selected collections."""
    bl_idname = "simple_export.set_export_paths"
    bl_label = "Assign Exporter Paths"
    bl_description = "Assign Exporter Pathss for selected collections based on the current naming conventions and folder settings."
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    # Internal Properties
    outliner: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    individual_collection: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    collection_name: bpy.props.StringProperty(
        name="Collection Name", default='',
        description="Name of the collection to process", options={'HIDDEN'}
    )
    # Stores outliner-selected collection names captured at invoke time,
    # because context.selected_ids is unavailable after the dialog opens.
    outliner_collection_names: bpy.props.StringProperty(default='', options={'HIDDEN'})

    # Operator Properties are inherited from the parent classes

    def draw(self, context):
        layout = self.layout

        box = layout.box()
        # Filepath settings
        from ..ui.shared_draw import draw_export_folderpath_properties, draw_export_filename_properties
        draw_export_filename_properties(box, self)

        box = layout.box()
        draw_export_folderpath_properties(box, self)

    def invoke(self, context, event):
        if self.outliner:
            cols = get_outliner_collections(context)
            self.outliner_collection_names = ','.join(c.name for c in cols)

        ref_col = self._get_reference_collection(context)

        if ref_col:
            addon_preset_name = getattr(ref_col, 'simple_export_addon_preset', '')
            if addon_preset_name:
                from ..presets_addon.exporter_preset import simple_export_presets_folder
                preset_path = os.path.join(simple_export_presets_folder(), f"{addon_preset_name}.py")
                if os.path.exists(preset_path):
                    self._apply_preset_props(preset_path)
                    return context.window_manager.invoke_props_dialog(self, width=400)

        # Fall back to scene's current values (set by the active addon preset)
        scene = context.scene
        for prop_name in _PATH_PROPS:
            if hasattr(scene, prop_name):
                try:
                    setattr(self, prop_name, getattr(scene, prop_name))
                except Exception:
                    pass

        return context.window_manager.invoke_props_dialog(self, width=400)

    def _apply_preset_props(self, preset_path):
        """Apply path/naming settings from an addon preset file to this operator."""
        from ..functions.preset_func import _parse_prefix_preset_file
        props = _parse_prefix_preset_file(preset_path, "scene")
        for prop_name in _PATH_PROPS:
            if prop_name in props:
                try:
                    setattr(self, prop_name, props[prop_name])
                except Exception:
                    pass

    def _get_reference_collection(self, context):
        """Return the first relevant collection to use as a reference for prefilling."""
        if self.individual_collection and self.collection_name:
            return bpy.data.collections.get(self.collection_name)
        if self.outliner:
            if self.outliner_collection_names:
                first_name = self.outliner_collection_names.split(',')[0]
                return bpy.data.collections.get(first_name)
            cols = get_outliner_collections(context)
            return cols[0] if cols else None
        if self.collection_name:
            col = bpy.data.collections.get(self.collection_name)
            if col:
                return col
        for col in bpy.data.collections:
            if getattr(col, 'simple_export_selected', False) and col.exporters:
                return col
        return None

    def execute(self, context):
        results = []
        scene = context.scene

        # Get Export Collections
        if self.outliner:
            if self.outliner_collection_names:
                names = [n for n in self.outliner_collection_names.split(',') if n]
                collection_list = [bpy.data.collections.get(n) for n in names]
                collection_list = [c for c in collection_list if c]
            else:
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
                if not collection.simple_export_selected and not self.individual_collection and not self.outliner:
                    continue
                if not collection.exporters:
                    continue
                collection = validate_collection(collection.name)
                if not collection:
                    continue

                # set exporter
                set_active_layer_Collection(collection.name)
                exporter = find_exporter(collection, format_filter=None)
                if not exporter:
                    continue

                exporter_op_type = str(type(exporter.export_properties))
                exporter_format_key = ExportFormats.get_key_from_op_type(exporter_op_type) or scene.export_format

                collection_name = collection.name

                export_folder, is_relative_path = get_export_folder_path(self.export_folder_mode,
                                                                         self.folder_path_absolute,
                                                                         self.folder_path_relative,
                                                                         self.folder_path_search,
                                                                         self.folder_path_replace)

                # Check for empty paths
                if not export_folder:
                    results.append({'name': collection.name, 'success': False, 'filepath': '',
                                    'message': "Export path is empty. Please specify a valid export folder."})
                    continue

                # FILE: filename properties
                filename = generate_base_name(collection_name, self.filename_prefix, self.filename_suffix,
                                              self.filename_blend_prefix, self.filename_separator)

                # Generate final export path
                export_path = generate_export_path(export_folder, filename, exporter_format_key,
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

        # Show result popup when started from Outliner
        if self.outliner:
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
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
