import bpy

from .shared_properties import (
    SharedPathProps, SharedFilenameProps,
    SharedPathAssignmentProps, SharedPresetAssignmentProps, CollectionNamingProps,
    CollectionOriginProps, CollectionSettingsProps, SharedFormatProps
)
from ..core.export_path_func import assign_exporter_path
from ..core.export_path_func import generate_base_name
from ..functions.collections_setup import setup_collection_properties
from ..functions.exporter_funcs import get_all_children_and_descendants
from ..functions.preset_func import assign_preset
from ..ui.shared_draw import draw_export_folderpath_properties


def determine_parent_collection(context, parent_collection_name="", top_object=None):
    """Determine the parent collection based on the specified hierarchy."""
    if parent_collection_name in bpy.data.collections:
        parent_collection_name = bpy.data.collections.get(parent_collection_name, None)
        if parent_collection_name:
            return parent_collection_name
    if parent_collection_name:
        from ..functions.collections_setup import create_collection
        return create_collection(parent_collection_name)
    if top_object and top_object.users_collection:
        return top_object.users_collection[0]
    return context.scene.collection


class EXPORT_OT_CreateExportCollections(
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
    """Create a new collection for each selected object and its children, preserving hierarchy."""
    bl_idname = "simple_export.create_export_collections"
    bl_label = "Create Export Collections"
    bl_description = "Create Export Collections for selected objects and their children, preserving hierarchy."
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}
    # TODO: Add support for adding exporters without selected objects

    # Internal Properties
    # only_selection: bpy.props.BoolProperty(
    #     name="Only affect selection",
    #     description="Only affect selected objects",
    #     default=False,
    #     options={'HIDDEN'}
    # )

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
                export_collection = setup_collection_properties(self, export_collection, top_object)

                # replace existing exporter
                from ..functions.exporter_funcs import create_collection_exporter, remove_all_collection_exporters
                remove_all_collection_exporters(export_collection)
                exporter = create_collection_exporter(self, context, export_collection)

                self.report({'INFO'},
                            f"Export collection '{export_collection.name}' created successfully for all objects.")
            else:
                self.report({'ERROR'}, "Failed to create export collection.")

            # Set preset
            if self.assign_preset:
                if self.assign_preset:
                    from ..presets_export.preset_format_functions import get_format_preset_filepath
                    preset_file = get_format_preset_filepath(self, self.export_format)
                    assign_preset(exporter, preset_file)

            if self.set_export_path and hasattr(exporter, 'filepath'):
                print(f"COLLECTION NAME = {export_collection.name}")
                assign_exporter_path(self, export_collection.name, exporter)

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
            parent_collection = determine_parent_collection(context, self.parent_collection, None)
            parent_collection.children.link(export_collection)

        for top_object in top_objects:
            # objects = context.selected_objects if self.only_selection else bpy.data.objects
            objects = bpy.data.objects

            hierarchy_objects = get_all_children_and_descendants(top_object)
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
        parent_collection = determine_parent_collection(context, self.parent_collection, top_object)
        if parent_collection:
            parent_collection.children.link(export_collection)
        else:
            self.report({'ERROR'}, "Failed to determine parent collection.")
            return None

        # objects = context.selected_objects if self.only_selection else bpy.data.objects
        # hierarchy_objects = get_all_children_and_descendants(top_object, objects)
        hierarchy_objects = get_all_children_and_descendants(top_object, include_top=True)
        # Link all hierarchy objects to the new collection

        for obj in hierarchy_objects:
            if export_collection not in obj.users_collection:
                export_collection.objects.link(obj)
            for col in obj.users_collection:
                if col != export_collection:
                    col.objects.unlink(obj)

        return export_collection

    def draw(self, context):
        """Draw the UI for the operator."""
        layout = self.layout
        from ..ui.shared_draw import draw_full_exporer_settings
        draw_full_exporer_settings(layout, self)



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
