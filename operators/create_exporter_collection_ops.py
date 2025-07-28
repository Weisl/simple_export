import bpy

from .shared_properties import (
    SharedPathProps, SharedFilenameProps,
    SharedPathAssignmentProps, SharedPresetAssignmentProps, CollectionNamingProps,
    CollectionOriginProps, CollectionSettingsProps
)
from ..core.export_formats import ExportFormats
from ..functions.collection_layer import set_active_layer_Collection
from ..functions.create_collection_func import generate_base_name
from ..functions.preset_func import set_preset
from ..ui.shared_draw import draw_export_folderpath_properties


# Context menu registration is now handled in ui/view3d_object_context_menu.py


class EXPORT_OT_CreateExportCollections(
    SharedPathAssignmentProps,
    SharedPresetAssignmentProps,
    CollectionNamingProps,
    CollectionOriginProps,
    CollectionSettingsProps,
    SharedPathProps,
    SharedFilenameProps,
    bpy.types.Operator
):
    """Create a new collection for each selected object and its children, preserving hierarchy."""
    bl_idname = "simple_export.create_export_collections"
    bl_label = "Create Export Collections"
    bl_options = {'REGISTER', 'UNDO'}

    # Internal Properties
    only_selection: bpy.props.BoolProperty(
        name="Only affect selection",
        description="Only affect selected objects",
        default=False,
        options={'HIDDEN'}
    )
    use_numbering: bpy.props.BoolProperty(
        name="Use Numbering",
        description="Add numbered suffix to collection names",
        default=False
    )

    def execute(self, context):
        """Execute the operator to create export collections."""
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}

        top_objects = [top_object for top_object in selected_objects if
                       not top_object.parent or top_object.parent not in selected_objects]

        if not self.collection_naming_overwrite or not self.collection_name_new:
            exporter_collections = self.create_individual_collections(context, top_objects)
        else:
            if self.use_numbering:
                exporter_collections = self.create_numbered_collections(context, top_objects)
            else:
                exporter_collections = self.create_single_collection(context, top_objects)

        for export_data in exporter_collections:
            if isinstance(export_data, tuple):
                export_collection, top_object = export_data
            else:
                export_collection = export_data
                top_object = None

            if export_collection is not None:
                export_collection = self.setup_collection_properties(export_collection, top_object)
                self.setup_exporter_assignments(context, export_collection)
                self.report({'INFO'},
                            f"Export collection '{export_collection.name}' created successfully for all objects.")
            else:
                self.report({'ERROR'}, "Failed to create export collection.")

        return {'FINISHED'}

    def create_individual_collections(self, context, top_objects):
        """Create individual collections for each selected object."""
        exporter_collections = []
        for top_object in top_objects:
            collection_name = generate_base_name(
                top_object.name,
                getattr(self, 'collection_prefix', ''),
                getattr(self, 'collection_suffix', ''),
                getattr(self, 'collection_blend_prefix', '')
            )
            # Skip creation if collection already exists
            if collection_name in bpy.data.collections:
                export_collection = bpy.data.collections[collection_name]
                self.report({'WARNING'}, f"Collection '{collection_name}' already exists. Using existing collection.")
            else:
                export_collection = self.create_and_setup_collection(context, collection_name, top_object)
            exporter_collections.append((export_collection, top_object))
        return exporter_collections

    def create_numbered_collections(self, context, top_objects):
        """Create numbered collections for each selected object."""
        exporter_collections = []
        for index, top_object in enumerate(top_objects):
            padded_index = f"{index:03}"
            collection_name = f"{self.collection_name_new}_{padded_index}"
            if collection_name in bpy.data.collections:
                export_collection = bpy.data.collections[collection_name]
                self.report({'WARNING'}, f"Collection '{collection_name}' already exists. Using existing collection.")
            else:
                export_collection = self.create_and_setup_collection(context, collection_name, top_object)
            exporter_collections.append((export_collection, top_object))
        return exporter_collections

    def create_single_collection(self, context, top_objects):
        """Create a single collection for all selected objects."""
        exporter_collections = []
        collection_name = self.collection_name_new
        if collection_name in bpy.data.collections:
            export_collection = bpy.data.collections[collection_name]
            self.report({'WARNING'}, f"Collection '{collection_name}' already exists. Using existing collection.")
        else:
            export_collection = bpy.data.collections.new(collection_name)
            parent_collection = self.determine_parent_collection(context, None)
            parent_collection.children.link(export_collection)

        for top_object in top_objects:
            objects = context.selected_objects if self.only_selection else bpy.data.objects
            hierarchy_objects = self.collect_children(top_object, objects)
            for obj in hierarchy_objects:
                if export_collection not in obj.users_collection:
                    export_collection.objects.link(obj)
                for col in obj.users_collection:
                    if col != export_collection:
                        col.objects.unlink(obj)

        if export_collection:
            exporter_collections.append((export_collection, top_object))
        return exporter_collections

    def create_and_setup_collection(self, context, collection_name, top_object):
        """Create a new collection and set it up with the given name and objects."""
        export_collection = bpy.data.collections.new(collection_name)
        parent_collection = self.determine_parent_collection(context, top_object)
        if parent_collection:
            parent_collection.children.link(export_collection)
        else:
            self.report({'ERROR'}, "Failed to determine parent collection.")
            return None

        objects = context.selected_objects if self.only_selection else bpy.data.objects
        hierarchy_objects = self.collect_children(top_object, objects)

        for obj in hierarchy_objects:
            if export_collection not in obj.users_collection:
                export_collection.objects.link(obj)
            for col in obj.users_collection:
                if col != export_collection:
                    col.objects.unlink(obj)

        return export_collection

    def setup_collection_properties(self, collection, base_object):
        """Set properties for the collection, such as color tag and offsets."""
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
        """Handle all exporter-related assignments for the collection."""
        if collection is None:
            self.report({'ERROR'}, "Collection is None in setup_exporter_assignments.")
            return

        exporter = self.assign_exporter_ops(context, collection)
        if exporter:
            self.set_preset_to_exporter(context, exporter)
            self.assign_filepath_to_exporter(context, collection, exporter)

    def assign_exporter_ops(self, context, collection):
        """Assign an exporter to the collection."""
        if collection is None:
            self.report({'ERROR'}, "Collection is None in assign_exporter_ops.")
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

    def set_preset_to_exporter(self, context, exporter):
        """Assign a preset to the exporter if set_preset is True and a preset filepath is provided."""
        if self.set_preset and self.preset_filepath:
            set_preset(exporter, self.preset_filepath)

    def assign_filepath_to_exporter(self, context, collection, exporter):
        """Assign a file path to the exporter if set_export_path is True and export folder settings are provided."""
        if not self.set_export_path or not hasattr(exporter, 'filepath'):
            return

        # Prepare a settings-like object for get_export_path
        class SettingsFilepath:
            export_folder_mode = self.export_folder_mode
            folder_path_absolute = self.folder_path_absolute
            folder_path_relative = self.folder_path_relative
            folder_path_search = self.folder_path_search
            folder_path_replace = self.folder_path_replace

        # Prepare a settings-like object for filename
        class SettingsFilename:
            filename_prefix = self.filename_prefix
            filename_suffix = self.filename_suffix
            filename_blend_prefix = self.filename_blend_prefix

        from ..core.export_path_func import get_export_path, generate_export_path
        from ..functions.create_collection_func import generate_base_name

        # Get export directory and relative mode
        export_dir, is_relative_path = get_export_path(SettingsFilepath, use_defaults=True)
        # Generate base name for the file
        base_name = generate_base_name(
            collection.name,
            self.filename_prefix,
            self.filename_suffix,
            self.filename_blend_prefix
        )
        # Generate the final export path
        scene = context.scene
        export_path = generate_export_path(
            base_name,
            scene.export_format,
            export_dir,
            is_relative_path=is_relative_path
        )
        exporter.filepath = export_path

    def determine_parent_collection(self, context, top_object):
        """Determine the parent collection based on the specified hierarchy."""
        if self.parent_collection_name:
            parent_collection = bpy.data.collections.get(self.parent_collection_name)
            if parent_collection:
                return parent_collection
        if hasattr(context.scene, 'parent_collection') and context.scene.parent_collection:
            return context.scene.parent_collection
        if top_object and top_object.users_collection:
            return top_object.users_collection[0]
        return context.scene.collection

    def collect_children(self, obj, objects):
        """Collect the object and its children."""
        children = [child for child in objects if child.parent == obj]
        return [obj] + children

    def draw(self, context):
        """Draw the UI for the operator."""
        layout = self.layout

        # --- Collection Name Section ---
        from ..ui.shared_draw import draw_collection_name_properties, draw_collection_settings_properties, \
            draw_export_preset_properties, draw_export_filename_properties
        box = layout.box()
        draw_collection_name_properties(box, self)

        # --- Collection Settings Section ---
        box = layout.box()
        draw_collection_settings_properties(box, self)

        # Optionally: add root object picker if use_root_object is True
        # box.prop(self, "root_object")

        # --- Preset Section ---
        box = layout.box()
        draw_export_preset_properties(box, self)

        # --- File Name Section ---
        box = layout.box()
        draw_export_filename_properties(box, self)

        # --- File Path Section ---
        box = layout.box()
        box.label(text="File Path")
        box.prop(self, "set_export_path")
        draw_export_folderpath_properties(box, self)


classes = (
    EXPORT_OT_CreateExportCollections,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
