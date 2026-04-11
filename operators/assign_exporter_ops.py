import os

import bpy

from .shared_properties import (
    SharedPathProps, SharedFilenameProps, SharedPathAssignmentProps, SharedPresetAssignmentProps, CollectionNamingProps,
    CollectionOriginProps, CollectionSettingsProps, SharedFormatProps
)
from ..core.export_path_func import assign_exporter_path
from ..functions.preset_func import assign_preset


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
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    # Internal Poperties
    collection_name: bpy.props.StringProperty(
        name="Collection Name",
        description="Name of the collection to modify",
        default="",
        options={'HIDDEN'}
    )

    existing_exporter_action: bpy.props.EnumProperty(
        name="Existing Exporter",
        description="How to handle the exporter already assigned to this collection",
        items=[
            ('REPLACE', "Replace", "Remove the existing exporter and replace it with a new one"),
            ('ADD', "Add New", "Keep the existing exporter and add a new one alongside it"),
            ('CANCEL', "Cancel", "Cancel the operation and leave the collection unchanged"),
        ],
        default='REPLACE'
    )

    def invoke(self, context, event):
        collection = bpy.data.collections.get(self.collection_name)
        if collection and collection.exporters:
            return context.window_manager.invoke_props_dialog(self, width=400)
        return self.execute(context)

    def draw(self, context):
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
            from ..ui.shared_draw import draw_full_exporer_settings
            draw_full_exporer_settings(layout, self)

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
            collection.last_preset_name = os.path.splitext(os.path.basename(preset_file))[0]

        selected_addon_preset = context.scene.simple_export_selected_preset
        if selected_addon_preset:
            collection.last_addon_preset_name = os.path.splitext(os.path.basename(selected_addon_preset))[0]

        # Assign filepath to exporter
        if self.set_export_path and hasattr(exporter, 'filepath'):
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
