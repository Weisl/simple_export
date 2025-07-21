import bpy

from ..functions.shared_draw import draw_operator_filepath_settings
from .shared_properties import (
    SharedPathProps, SharedFilenameProps, SharedPathAssignmentProps, SharedPresetAssignmentProps, CollectionNamingProps,
    CollectionOriginProps, CollectionSettingsProps
)
from ..core.export_formats import ExportFormats
from ..functions.collection_layer import set_active_layer_Collection
from ..functions.preset_func import assign_preset


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

        # Set collection properties (color, offset, etc.)
        self.setup_collection_properties(collection, None)

        # Assign exporter, preset, and filepath
        self.setup_exporter_assignments(context, collection)

        self.report({'INFO'}, f"Settings applied to collection '{collection.name}'.")
        return {'FINISHED'}

    def setup_collection_properties(self, collection, base_object):
        collection.simple_export_selected = True
        if self.collection_color != 'NONE':
            collection.color_tag = self.collection_color
        if self.collection_instance_offset and hasattr(collection, 'instance_offset'):
            collection.instance_offset = base_object.location if base_object else (0, 0, 0)
        if self.use_root_object and hasattr(collection, 'use_root_object'):
            collection.use_root_object = self.use_root_object
        if self.use_root_object and base_object:
            collection.root_object = base_object
        return collection

    def setup_exporter_assignments(self, context, collection):
        if collection is None:
            self.report({'ERROR'}, "Collection is None in setup_exporter_assignments.")
            return
        exporter = self.assign_exporter(context, collection)
        if exporter:
            self.assign_preset_to_exporter(context, exporter)
            self.assign_filepath_to_exporter(context, collection, exporter)

    def assign_exporter(self, context, collection):
        if collection is None:
            self.report({'ERROR'}, "Collection is None in assign_exporter.")
            return None
        scene = context.scene
        set_active_layer_Collection(collection.name)
        export_data = ExportFormats.get(scene.export_format)
        if not export_data:
            self.report({'ERROR'}, f"Invalid export format: {scene.export_format}")
            return None

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

    def assign_preset_to_exporter(self, context, exporter):
        if self.assign_preset and self.preset_filepath:
            assign_preset(exporter, self.preset_filepath)

    def assign_filepath_to_exporter(self, context, collection, exporter):
        if not self.assign_export_filepath or not hasattr(exporter, 'filepath'):
            return

        class SettingsFilepath:
            export_folder_mode = self.export_folder_mode
            folder_path_absolute = self.folder_path_absolute
            folder_path_relative = self.folder_path_relative
            folder_path_search = self.folder_path_search
            folder_path_replace = self.folder_path_replace

        class SettingsFilename:
            filename_prefix = self.filename_prefix
            filename_suffix = self.filename_suffix
            filename_blend_prefix = self.filename_blend_prefix

        from ..core.export_path_func import get_export_path, generate_export_path
        from ..functions.create_collection_func import generate_base_name
        export_dir, is_relative_path = get_export_path(SettingsFilepath, use_defaults=True)
        base_name = generate_base_name(
            collection.name,
            self.filename_prefix,
            self.filename_suffix,
            self.filename_blend_prefix
        )
        scene = context.scene
        export_path = generate_export_path(
            base_name,
            scene.export_format,
            export_dir,
            is_relative_path=is_relative_path
        )
        exporter.filepath = export_path

    def draw(self, context):
        layout = self.layout
        # --- Collection Name Section ---
        box = layout.box()
        box.label(text="Collection Name")
        box.prop(self, "collection_naming_overwrite")
        if self.collection_naming_overwrite:
            box.prop(self, "collection_name_new")
            box.prop(self, "use_numbering")
        box.prop(self, "collection_file_name_prefix")
        box.prop(self, "collection_prefix")
        box.prop(self, "collection_suffix")
        # --- Collection Settings Section ---
        box = layout.box()
        box.label(text="Collection Settings")
        box.prop(self, "collection_color")
        box.prop(self, "collection_instance_offset")
        box.prop(self, "use_root_object")
        # --- Preset Section ---
        box = layout.box()
        box.label(text="Export Preset")
        box.prop(self, "assign_preset")
        box.prop(self, "preset_filepath")
        # --- File Name Section ---
        box = layout.box()
        box.label(text="File Name")
        box.prop(self, "filename_blend_prefix")
        box.prop(self, "filename_prefix")
        box.prop(self, "filename_suffix")
        # --- File Path Section ---
        box = layout.box()
        box.label(text="File Path")
        box.prop(self, "assign_export_filepath")
        draw_operator_filepath_settings(box, self)


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
