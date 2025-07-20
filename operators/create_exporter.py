import bpy

from ..core.export_formats import ExportFormats
from ..core.export_path_func import assign_export_path_to_exporter
from ..functions.collection_layer import set_active_layer_Collection
from ..functions.create_collection_func import generate_base_name
from ..functions.preset_func import assign_preset


class EXPORT_OT_CreateExportCollections(bpy.types.Operator):
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


    # User-facing Properties
    overwrite_naming: bpy.props.BoolProperty(
        name="Overwrite Naming",
        description="Overwrite the naming for the newly created export collections",
        default=False
    )

    overwrite_collection_name: bpy.props.StringProperty(
        name="Name",
        description="Overwrite the name for the newly created export collection",
        default=""
    )

    use_numbering: bpy.props.BoolProperty(
        name="Use Numbering",
        description="Add numbered suffix to collection names",
        default=False
    )

    parent_collection_name: bpy.props.StringProperty(
        name="Parent Collection",
        description="Name of the parent collection for the new collections",
        default=""
    )

    from ..preferences.preferenecs import PROPERTY_METADATA
    collection_color: bpy.props.EnumProperty(
        name=PROPERTY_METADATA["collection_color"]["name"],
        description=PROPERTY_METADATA["collection_color"]["description"],
        items=PROPERTY_METADATA["collection_color"]["items"],
        default=PROPERTY_METADATA["collection_color"]["default"],
    )

    collection_instance_offset: bpy.props.BoolProperty(
        name="Set Instance Offset",
        description="Set instance offset for the collection",
        default=False
    )

    use_root_object: bpy.props.BoolProperty(
        name="Use Root Object",
        description="Use a root object for the collection",
        default=True
    )

    preset_filepath: bpy.props.StringProperty(
        name="Preset",
        description="Path to the preset file to assign to the exporter",
        default="",
        subtype='FILE_PATH'
    )

    export_filepath: bpy.props.StringProperty(
        name="Folder",
        description="Filepath for the export",
        default="",
        subtype='DIR_PATH'
    )

    collection_custom_prefix: bpy.props.StringProperty(
        name="Custom Prefix",
        description="Custom prefix for collection names",
        default=""
    )

    collection_custom_suffix: bpy.props.StringProperty(
        name="Custom Suffix",
        description="Custom suffix for collection names",
        default=""
    )

    collection_file_name_prefix: bpy.props.BoolProperty(
        name="Use File Name as Prefix",
        description="Use the blend file name as prefix for collection names",
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

        if not self.overwrite_naming or not self.overwrite_collection_name:
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
                getattr(self, 'collection_custom_prefix', ''),
                getattr(self, 'collection_custom_suffix', ''),
                getattr(self, 'collection_file_name_prefix', '')
            )
            export_collection = self.create_and_setup_collection(context, collection_name, top_object)
            if export_collection:
                exporter_collections.append((export_collection, top_object))
        return exporter_collections

    def create_numbered_collections(self, context, top_objects):
        """Create numbered collections for each selected object."""
        exporter_collections = []
        for index, top_object in enumerate(top_objects):
            padded_index = f"{index:03}"
            collection_name = f"{self.overwrite_collection_name}_{padded_index}"
            export_collection = self.create_and_setup_collection(context, collection_name, top_object)
            if export_collection:
                exporter_collections.append((export_collection, top_object))
        return exporter_collections

    def create_single_collection(self, context, top_objects):
        """Create a single collection for all selected objects."""
        exporter_collections = []
        collection_name = self.overwrite_collection_name
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

        exporter = self.assign_exporter(context, collection)
        if exporter:
            self.assign_preset_to_exporter(context, exporter)
            self.assign_filepath_to_exporter(context, collection, exporter)

    def assign_exporter(self, context, collection):
        """Assign an exporter to the collection."""
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
        """Assign a preset to the exporter if a preset filepath is provided."""
        if self.preset_filepath:
            assign_preset(exporter, self.preset_filepath)

    def assign_filepath_to_exporter(self, context, collection, exporter):
        """Assign a file path to the exporter if an export filepath is provided."""
        if self.export_filepath and hasattr(exporter, 'filepath'):
            exporter.filepath = self.export_filepath


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
        
        # Naming settings
        box = layout.box()
        box.label(text="Naming Settings:")
        box.prop(self, "overwrite_naming")
        if self.overwrite_naming:
            box.prop(self, "overwrite_collection_name")
            box.prop(self, "use_numbering")
        
        layout.prop(self, "use_root_object")
        layout.prop(self, "collection_color")
        layout.prop_search(self, "parent_collection_name", bpy.data, "collections")
        
        # Preset and filepath settings
        box = layout.box()
        box.label(text="Preset")
        box.prop(self, "preset_filepath")

        box = layout.box()
        box.label(text="Export Folder:")
        box.prop(self, "export_filepath")


def add_export_collections_to_menu(self, context):
    """Adds the Simple Export create export collections operator to the object context menu."""
    self.layout.separator()
    op = self.layout.operator("simple_export.create_export_collections", icon='COLLECTION_COLOR_01')
    
    # Set default properties
    op.only_selection = True
    op.overwrite_naming = False
    op.overwrite_collection_name = ""
    op.use_numbering = False
    op.parent_collection_name = context.scene.parent_collection.name if context.scene.parent_collection else ""
    
    # Get and set properties from preferences/scene
    from ..ui.export_panels import get_operator_properties
    props = get_operator_properties(context)
    op.collection_custom_prefix = props['collection_custom_prefix']
    op.collection_custom_suffix = props['collection_custom_suffix']
    op.collection_file_name_prefix = props['collection_file_name_prefix']
    op.collection_color = props['collection_color']
    op.collection_instance_offset = props['collection_instance_offset']
    op.use_root_object = props['use_root_object']
    op.preset_filepath = props['preset_filepath']
    op.export_filepath = props['export_filepath']


classes = (
    EXPORT_OT_CreateExportCollections,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)
    bpy.types.VIEW3D_MT_object_context_menu.append(add_export_collections_to_menu)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
    bpy.types.VIEW3D_MT_object_context_menu.remove(add_export_collections_to_menu)
