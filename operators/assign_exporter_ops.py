import bpy

from .shared_properties import (
    SharedPathProps, SharedFilenameProps, SharedPathAssignmentProps, SharedPresetAssignmentProps, CollectionNamingProps,
    CollectionOriginProps, CollectionSettingsProps
)
from ..core.export_path_func import get_export_folder_path, generate_base_name, generate_export_path
from ..functions.exporter_funcs import assign_collection_exporter
from ..functions.preset_func import set_preset


class EXPORT_OT_AddSettingsToCollections(
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

        exporter = assign_collection_exporter(self, context, collection)

        if not exporter:
            self.report({'INFO'}, f"Exporter was not added to '{collection.name}'.")
            return {'FINISHED'}

        # Set preset
        if self.set_preset and self.preset_filepath:
            set_preset(exporter, self.preset_filepath)

        # Assign filepath to exporter
        if self.set_export_path and hasattr(exporter, 'filepath'):

            export_folder, is_relative_path = get_export_folder_path(self.export_folder_mode, self.folder_path_absolute,
                                                                     self.folder_path_relative,
                                                                     self.folder_path_search, self.folder_path_replace)

            # FILE: filename properties
            filename = generate_base_name(self.collection_name, self.filename_prefix, self.filename_suffix,
                                          self.filename_blend_prefix)

            # Generate final export path
            export_path = generate_export_path(export_folder, filename, context.scene.export_format,
                                               is_relative_path=is_relative_path)

            # 3. Assign to exporter
            if export_path:
                exporter.filepath = export_path

        self.report({'INFO'}, f"Settings applied to collection '{collection.name}'.")
        return {'FINISHED'}

        def get_all_exporters():
            return list(collection.exporters)

        exporters_before = get_all_exporters()
        operator_name = export_data.op_name
        bpy.ops.collection.exporter_add(name=operator_name)
        exporters_after = get_all_exporters()
        new_exporters = set(exporters_after) - set(exporters_before)
        if new_exporters:
            return new_exporters.pop()
        else:
            self.report({'ERROR'}, "Failed to add a new exporter.")
            return None

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
