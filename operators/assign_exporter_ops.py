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

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)

        if not collection:
            self.report({'ERROR'}, f"Collection '{self.collection_name}' not found.")
            return {'CANCELLED'}

        # Optionally rename
        if self.collection_naming_overwrite and self.collection_name_new:
            collection.name = self.collection_name_new

        from ..functions.collections_setup import setup_collection_properties
        setup_collection_properties(self, collection, base_object=None)

        # replace existing exporter
        from ..functions.exporter_funcs import create_collection_exporter,remove_all_collection_exporters
        remove_all_collection_exporters(collection)
        exporter = create_collection_exporter(self, context, collection)

        if not exporter:
            self.report({'INFO'}, f"Exporter was not added to '{collection.name}'.")
            return {'FINISHED'}

        # Set preset
        if self.assign_preset and self.preset_filepath:
            assign_preset(exporter, self.preset_filepath)

        # Assign filepath to exporter
        if self.set_export_path and hasattr(exporter, 'filepath'):
            assign_exporter_path(self, collection.name, exporter)

        self.report({'INFO'}, f"Settings applied to collection '{collection.name}'.")
        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        # --- Collection Name Section ---

        box = layout.box()
        from ..ui.shared_draw import draw_collection_name_properties
        draw_collection_name_properties(box, self)

        # --- Collection Settings Section ---
        box = layout.box()
        from ..ui.shared_draw import draw_collection_settings_properties
        draw_collection_settings_properties(box, self)

        # --- Preset Section ---
        from ..ui.shared_draw import draw_export_preset_properties
        box = layout.box()
        draw_export_preset_properties(box, self)

        # --- File Name Section ---
        from ..ui.shared_draw import draw_export_filename_properties
        box = layout.box()
        draw_export_filename_properties(box, self)

        # --- File Path Section ---
        box = layout.box()
        from ..ui.shared_draw import draw_export_folderpath_properties
        draw_export_folderpath_properties(box, self)


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
        unregister_class(cls)
