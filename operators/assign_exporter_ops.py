import bpy

from .shared_properties import (
    SharedPathProps, SharedFilenameProps, SharedPathAssignmentProps, SharedPresetAssignmentProps, CollectionNamingProps,
    CollectionOriginProps, CollectionSettingsProps
)
from ..functions.exporter_funcs import assign_collection_exporter
from ..functions.preset_func import set_preset



def _generate_export_path(self, data):
    """Generate the export path from retrieved data."""


    
    from ..core.export_path_func import get_export_path, generate_export_path
    from ..functions.create_collection_func import generate_base_name
    
    export_folder_mode = self.export_folder_mode
    folder_path_absolute = self.folder_path_absolute
    folder_path_relative = self.folder_path_relative
    folder_path_search = self.folder_path_search
    folder_path_replace = self.folder_path_replace
    
    # Get export directory and relative mode
    export_dir, is_relative_path = get_export_path(data['settings_filepath'], use_defaults=True)
    
    # Generate base name for the file
    base_name = generate_base_name(collection.name, self.filename_prefix, self.filename_suffix, filename_blend_prefix)
    
    # Generate the final export path
    export_path = generate_export_path(
        base_name,
        data['scene'].export_format,
        export_dir,
        is_relative_path=is_relative_path
    )
    
    return export_path





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
    bl_options = {'REGISTER', 'UNDO'}

    # Hidden property for the collection name
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

        if exporter:
            if self.set_preset and self.preset_filepath:
                set_preset(exporter, self.preset_filepath)
            
            # Assign filepath to exporter
            if self.set_export_path and hasattr(exporter, 'filepath'):
                # 1. Retrieve data
                data = self._retrieve_filepath_data(context, collection)
                
                # 2. Generate export path
                export_path = self._generate_export_path(data)
                
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
