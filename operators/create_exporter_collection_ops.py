import bpy

from .shared_properties import (
    SharedPathProps, SharedFilenameProps,
    SharedPathAssignmentProps, SharedPresetAssignmentProps, CollectionNamingProps,
    CollectionOriginProps, CollectionSettingsProps
)
from ..core.export_formats import ExportFormats
from ..functions.create_collection_func import generate_base_name
from ..functions.collection_utils import setup_collection_properties, determine_parent_collection, collect_children
from ..functions.exporter_utils import setup_exporter_assignments
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
            parent_collection = determine_parent_collection(context, self.parent_collection_name, None)
            parent_collection.children.link(export_collection)

        for top_object in top_objects:
            objects = context.selected_objects if self.only_selection else bpy.data.objects
            hierarchy_objects = collect_children(top_object, objects)
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
        parent_collection = determine_parent_collection(context, self.parent_collection_name, top_object)
        if parent_collection:
            parent_collection.children.link(export_collection)
        else:
            self.report({'ERROR'}, "Failed to determine parent collection.")
            return None

        objects = context.selected_objects if self.only_selection else bpy.data.objects
        hierarchy_objects = collect_children(top_object, objects)

        for obj in hierarchy_objects:
            if export_collection not in obj.users_collection:
                export_collection.objects.link(obj)
            for col in obj.users_collection:
                if col != export_collection:
                    col.objects.unlink(obj)

        return export_collection

    def setup_collection_properties(self, collection, base_object):
        """Set properties for the collection, such as color tag and offsets."""
        return setup_collection_properties(
            collection, base_object, 
            self.collection_color, 
            self.collection_instance_offset, 
            self.use_root_object
        )

    def setup_exporter_assignments(self, context, collection):
        """Handle all exporter-related assignments for the collection."""
        if collection is None:
            self.report({'ERROR'}, "Collection is None in setup_exporter_assignments.")
            return

        success = setup_exporter_assignments(
            context, collection,
            self.set_preset, self.preset_filepath,
            self.set_export_path, self.export_folder_mode,
            self.folder_path_absolute, self.folder_path_relative,
            self.folder_path_search, self.folder_path_replace,
            self.filename_prefix, self.filename_suffix, self.filename_blend_prefix
        )
        if not success:
            self.report({'ERROR'}, "Failed to setup exporter assignments.")



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
