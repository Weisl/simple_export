import os

import bpy

from .shared_properties import (
    SharedPathProps, SharedFilenameProps, SharedPathAssignmentProps, SharedPresetAssignmentProps, CollectionNamingProps,
    CollectionOriginProps, CollectionSettingsProps, SharedFormatProps
)
from ..core.export_path_func import assign_exporter_path
from ..functions.outliner_func import get_outliner_collections
from ..functions.preset_func import assign_preset


def get_addon_preset_items(self, context):
    from ..presets_addon.exporter_preset import simple_export_presets_folder
    folder = simple_export_presets_folder()
    items = []
    if os.path.isdir(folder):
        for fname in sorted(os.listdir(folder)):
            if fname.endswith('.py'):
                name = os.path.splitext(fname)[0]
                items.append((name, name, ""))
    return items if items else [('NONE', "No Presets Available", "")]


class EXPORT_OT_AddSettingsToCollections(
    SharedFormatProps,
    SharedPathAssignmentProps,
    SharedPresetAssignmentProps,
    CollectionNamingProps,
    CollectionOriginProps,
    CollectionSettingsProps,
    SharedPathProps,
    SharedFilenameProps,
    bpy.types.Operator
):
    """
    Add export settings to an existing collection.
    """
    bl_idname = "simple_export.add_settings_to_collections"
    bl_label = "Add Exporter to Collection"
    bl_description = "Adds an Exporter to a Collection together with all exporter settings."
    bl_options = {'REGISTER', 'UNDO'}

    # Internal Properties
    collection_name: bpy.props.StringProperty(
        name="Collection Name",
        description="Name of the collection to modify",
        default="",
        options={'HIDDEN'}
    )

    outliner: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    # Stores outliner-selected collection names captured at invoke time,
    # because context.selected_ids is unavailable after the dialog opens.
    outliner_collection_names: bpy.props.StringProperty(default='', options={'HIDDEN'})

    addon_preset_selection: bpy.props.EnumProperty(
        name="Preset",
        description="Simple Export addon preset to use for this collection",
        items=get_addon_preset_items,
    )

    applied_preset_tracker: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    _PRESET_SKIP_PROPS: set = set()

    def _apply_addon_preset_to_self(self, preset_path):
        """Parse an addon preset file and apply its scene.* values to operator properties."""
        if not os.path.isfile(preset_path):
            return
        with open(preset_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line.startswith('scene.'):
                    continue
                try:
                    prop_part = line[6:]  # strip 'scene.'
                    prop_name, value_str = prop_part.split(' = ', 1)
                    if prop_name in self._PRESET_SKIP_PROPS:
                        continue
                    if hasattr(self, prop_name):
                        setattr(self, prop_name, eval(value_str))
                except Exception:
                    pass

    def check(self, context):
        if self.addon_preset_selection == self.applied_preset_tracker:
            return False
        self.applied_preset_tracker = self.addon_preset_selection
        if self.addon_preset_selection and self.addon_preset_selection != 'NONE':
            from ..presets_addon.exporter_preset import simple_export_presets_folder
            preset_path = os.path.join(
                simple_export_presets_folder(),
                self.addon_preset_selection + '.py'
            )
            self._apply_addon_preset_to_self(preset_path)
        return True

    def invoke(self, context, event):
        if self.outliner:
            cols = get_outliner_collections(context)
            self.outliner_collection_names = ','.join(c.name for c in cols)

        self.applied_preset_tracker = ""
        selected = context.scene.simple_export_selected_preset
        if selected:
            name = os.path.splitext(os.path.basename(selected))[0]
            try:
                self.addon_preset_selection = name
            except Exception:
                pass
        return context.window_manager.invoke_props_dialog(self, width=400)

    def draw(self, context):
        from .. import __package__ as base_package
        layout = self.layout

        if self.outliner:
            names = [n for n in self.outliner_collection_names.split(',') if n]
            if len(names) > 1:
                layout.label(text=f"Applies to {len(names)} selected collections", icon='INFO')

        layout.prop(self, "addon_preset_selection", text="")
        from ..core.info import ADDON_NAME
        op = layout.operator("simple_export.open_preferences", text="New Preset", icon='PREFERENCES')
        op.addon_name = ADDON_NAME
        op.prefs_tabs = 'SETTINGS'

        layout.separator()
        layout.prop(self, "set_export_path")
        if self.set_export_path:
            from ..ui.shared_draw import draw_export_folderpath_properties
            draw_export_folderpath_properties(layout, self)

    def execute(self, context):
        if self.outliner:
            return self._execute_batch(context)

        collection = bpy.data.collections.get(self.collection_name)

        if not collection:
            self.report({'ERROR'}, f"Collection '{self.collection_name}' not found.")
            return {'CANCELLED'}

        # Optionally rename
        if self.collection_naming_overwrite and self.collection_name_new:
            collection.name = self.collection_name_new

        result = self._apply_settings(context, collection)
        self.report({'INFO'}, result['message'])
        return {'FINISHED'}

    def _execute_batch(self, context):
        """Apply settings to every collection selected in the Outliner."""
        if self.outliner_collection_names:
            names = [n for n in self.outliner_collection_names.split(',') if n]
            collection_list = [bpy.data.collections.get(n) for n in names]
            collection_list = [c for c in collection_list if c]
        else:
            collection_list = get_outliner_collections(context)

        if not collection_list:
            self.report({'WARNING'}, "No collections selected in the Outliner.")
            return {'CANCELLED'}

        results = []
        for collection in collection_list:
            try:
                results.append(self._apply_settings(context, collection))
            except Exception as e:
                results.append({'name': collection.name, 'success': False, 'message': str(e)})

        success_count = sum(1 for r in results if r['success'])
        self.report({'INFO'}, f"Added exporter to {success_count}/{len(results)} collection(s).")

        context.window_manager.add_exporter_result_info = str(results)
        bpy.ops.wm.call_panel(name="SIMPLEEXPORTER_PT_AddExporterResultsPanel")

        return {'FINISHED'}

    def _apply_settings(self, context, collection):
        """Add/replace the exporter and apply settings on a single collection. Returns a result dict."""
        from ..functions.collections_setup import setup_collection_properties
        setup_collection_properties(self, collection, base_object=None)

        from ..functions.exporter_funcs import create_collection_exporter, remove_all_collection_exporters
        if collection.exporters:
            remove_all_collection_exporters(collection)
        exporter = create_collection_exporter(self, context, collection)

        if not exporter:
            return {'name': collection.name, 'success': False,
                    'message': f"Exporter was not added to '{collection.name}'."}

        # Set preset
        if self.assign_preset:
            from ..presets_export.preset_format_functions import get_format_preset_filepath
            preset_file = get_format_preset_filepath(self, self.export_format)
            assign_preset(exporter, preset_file)
            collection.simple_export_export_preset = os.path.splitext(os.path.basename(preset_file))[0]

        if self.addon_preset_selection and self.addon_preset_selection != 'NONE':
            collection.simple_export_addon_preset = self.addon_preset_selection

        # Assign filepath to exporter
        if self.set_export_path and hasattr(exporter, 'export_properties'):
            assign_exporter_path(self, collection.name, exporter)

        return {'name': collection.name, 'success': True,
                'message': f"Settings applied to collection '{collection.name}'."}


classes = (
    EXPORT_OT_AddSettingsToCollections,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
