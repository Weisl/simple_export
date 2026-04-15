import os

import bpy

from .shared_properties import (
    SharedPathProps, SharedFilenameProps, SharedPathAssignmentProps, SharedPresetAssignmentProps, CollectionNamingProps,
    CollectionOriginProps, CollectionSettingsProps, SharedFormatProps
)
from ..core.export_path_func import assign_exporter_path
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

    existing_exporter_action: bpy.props.EnumProperty(
        name="Existing Exporter",
        description="How to handle the exporter already assigned to this collection",
        items=[
            ('ADD', "Add New", "Keep the existing exporter and add a new one alongside it"),
            ('REPLACE', "Replace", "Remove the existing exporter and replace it with a new one"),
            ('CANCEL', "Cancel", "Cancel the operation and leave the collection unchanged"),
        ],
        default='ADD'
    )

    def invoke(self, context, event):
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
        collection = bpy.data.collections.get(self.collection_name)
        if collection and collection.exporters:
            col = layout.column(align=True)
            col.label(text=f"'{collection.name}' already has an exporter assigned.", icon='ERROR')
            col.separator()
            col.label(text="How would you like to proceed?")
            col.separator()
            col.prop(self, "existing_exporter_action", expand=True)
        else:
            layout.prop(self, "addon_preset_selection", text="")
            op = layout.operator("preferences.addon_show", text="New Preset", icon='PREFERENCES')
            op.module = base_package

            layout.separator()
            layout.prop(self, "set_export_path")
            if self.set_export_path:
                from ..ui.shared_draw import draw_export_folderpath_properties
                draw_export_folderpath_properties(layout, self)

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)

        if not collection:
            self.report({'ERROR'}, f"Collection '{self.collection_name}' not found.")
            return {'CANCELLED'}

        # Handle choice when collection already has exporters
        if collection.exporters:
            if self.existing_exporter_action == 'CANCEL':
                self.report({'INFO'}, "Operation cancelled.")
                return {'CANCELLED'}

        # Optionally rename
        if self.collection_naming_overwrite and self.collection_name_new:
            collection.name = self.collection_name_new

        from ..functions.collections_setup import setup_collection_properties
        setup_collection_properties(self, collection, base_object=None)

        from ..functions.exporter_funcs import create_collection_exporter, remove_all_collection_exporters
        if collection.exporters and self.existing_exporter_action == 'REPLACE':
            remove_all_collection_exporters(collection)
        exporter = create_collection_exporter(self, context, collection)

        if not exporter:
            self.report({'INFO'}, f"Exporter was not added to '{collection.name}'.")
            return {'FINISHED'}

        # Set preset
        if self.assign_preset:
            from ..presets_export.preset_format_functions import get_format_preset_filepath
            preset_file = get_format_preset_filepath(self, self.export_format)
            assign_preset(exporter, preset_file)
            collection.simple_export_export_preset = os.path.splitext(os.path.basename(preset_file))[0]

        selected_addon_preset = context.scene.simple_export_selected_preset
        if selected_addon_preset:
            collection.simple_export_export_preset = os.path.splitext(os.path.basename(selected_addon_preset))[0]

        # Assign filepath to exporter
        if self.set_export_path and exporter and hasattr(exporter, 'export_properties'):
            assign_exporter_path(self, collection.name, exporter)

        self.report({'INFO'}, f"Settings applied to collection '{collection.name}'.")
        return {'FINISHED'}


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
