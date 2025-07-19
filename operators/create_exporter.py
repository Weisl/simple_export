import bpy

from .. import __package__ as base_package
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
    overwrite_collection_name: bpy.props.StringProperty(
        name="Overwrite Collection Name",
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

    set_collection_root: bpy.props.BoolProperty(
        name="Set Root Object",
        description="Set a root object to define the Collection Offset center.",
        default=True
    )

    from ..preferences.preferenecs import PROPERTY_METADATA

    collection_color: bpy.props.EnumProperty(
        name=PROPERTY_METADATA["collection_color"]["name"],
        description=PROPERTY_METADATA["collection_color"]["description"],
        items=PROPERTY_METADATA["collection_color"]["items"],
        default=PROPERTY_METADATA["collection_color"]["default"],
    )

    # TODO: Property for overwriting filepath setting
    # TODO: Property for overwritting root object
    # TODO: Property for overwriting preset settings
    # TODO: Property for overwriting file format

    def execute(self, context):
        """Execute the operator to create export collections."""
        # Check if any objects are selected
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}

        # Get the preferences and scene settings
        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene
        settings_col = scene if scene.overwrite_collection_settings else prefs

        # Determine list of new collections to create
        top_objects = [top_object for top_object in selected_objects if
                       not top_object.parent or top_object.parent not in selected_objects]

        # Get list of exporter collections
        if not self.overwrite_collection_name:
            exporter_collections = self.create_individual_collections(context, top_objects, settings_col)
        else:  # If a collection name is provided, create collections based on that
            if self.use_numbering:
                exporter_collections = self.create_numbered_collections(context, top_objects, settings_col)
            else:
                exporter_collections = self.create_single_collection(context, top_objects, settings_col)

        # Setup exporter for each collection
        for export_collection in exporter_collections:
            self.setup_exporter_assignments(context, export_collection, prefs)
            self.report({'INFO'}, f"Export collection '{export_collection.name}' created successfully for all objects.")

        return {'FINISHED'}

    def create_individual_collections(self, context, top_objects, settings_col):
        """Create individual collections for each selected object."""
        exporter_collections = []
        for top_object in top_objects:
            collection_name = generate_base_name(
                top_object.name,
                getattr(settings_col, 'collection_custom_prefix', ''),
                getattr(settings_col, 'collection_custom_suffix', ''),
                getattr(settings_col, 'collection_file_name_prefix', '')
            )
            export_collection = self.create_and_setup_collection(context, collection_name, top_object)
            col = self.setup_collection_properties(export_collection, top_object, settings_col)
            exporter_collections.append(col)
        return exporter_collections

    def create_numbered_collections(self, context, top_objects, settings_col):
        """Create numbered collections for each selected object."""
        exporter_collections = []

        for index, top_object in enumerate(top_objects):
            padded_index = f"{index:03}"
            collection_name = f"{self.overwrite_collection_name}_{padded_index}"
            export_collection = self.create_and_setup_collection(context, collection_name, top_object)
            col = self.setup_collection_properties(export_collection, top_object, settings_col)
            exporter_collections.append(col)
        return exporter_collections

    def create_single_collection(self, context, top_objects, settings_col):
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

        col = self.setup_collection_properties(export_collection, None, settings_col)
        exporter_collections.append(col)
        return exporter_collections

    def create_and_setup_collection(self, context, collection_name, top_object):
        """Create a new collection and set it up with the given name and objects."""
        export_collection = bpy.data.collections.new(collection_name)
        parent_collection = self.determine_parent_collection(context, top_object)
        parent_collection.children.link(export_collection)

        objects = context.selected_objects if self.only_selection else bpy.data.objects
        hierarchy_objects = self.collect_children(top_object, objects)

        for obj in hierarchy_objects:
            if export_collection not in obj.users_collection:
                export_collection.objects.link(obj)
            for col in obj.users_collection:
                if col != export_collection:
                    col.objects.unlink(obj)

        return export_collection

    def setup_collection_properties(self, collection, active_object, settings_col):
        """Set properties for the collection, such as color tag and offsets."""
        collection.simple_export_selected = True
        if self.collection_color != 'NONE':
            collection.color_tag = self.collection_color
        if getattr(settings_col, 'collection_set_location_offset_on_creation'):
            collection.instance_offset = active_object.location if active_object else (0, 0, 0)
        if getattr(settings_col, 'collection_use_root_offset_object'):
            collection.use_root_object = settings_col.collection_use_root_offset_object
        if getattr(settings_col, 'collection_set_root_offset_object') and active_object:
            collection.root_object = active_object

    def setup_exporter_assignments(self, context, collection, prefs):
        """Handle all exporter-related assignments for the collection."""
        exporter = self.assign_exporter(context, collection)
        if exporter:
            self.assign_preset_to_exporter(context, exporter, settings_col, prefs)
            self.assign_filepath_to_exporter(context, collection, exporter, settings_col, prefs)

    def assign_exporter(self, context, collection):
        """Assign an exporter to the collection."""
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

        # Find the newly added exporter
        new_exporters = set(exporters_after) - set(exporters_before)
        if new_exporters:
            return new_exporters.pop()
        else:
            self.report({'ERROR'}, "Failed to add a new exporter.")
            return None

    def assign_preset_to_exporter(self, context, exporter, settings_col, prefs):
        """Assign a preset to the exporter if auto-set is enabled."""
        scene = context.scene
        if getattr(settings_col, 'collection_auto_set_preset'):
            export_format = scene.export_format.lower()
            prop_name = f"simple_export_preset_file_{export_format}"
            preset_settings = scene if scene.overwrite_preset_settings else prefs
            preset_path = getattr(preset_settings, prop_name, None)
            if preset_path:
                assign_preset(exporter, preset_path)
            else:
                self.report({'WARNING'}, "No preset path found for the exporter.")

    def assign_filepath_to_exporter(self, context, collection, exporter, settings_col, prefs):
        """Assign a file path to the exporter if auto-set is enabled."""
        scene = context.scene
        if getattr(settings_col, 'collection_auto_set_filepath'):
            success, export_path, msg = assign_export_path_to_exporter(
                collection, exporter, scene, prefs, prefs, use_defaults=True)
            if not success:
                self.report({'WARNING'}, f"Failed to assign export path: {msg}")

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
        layout.prop(self, "overwrite_collection_name")
        layout.prop(self, "use_numbering")
        layout.prop(self, "set_collection_root")
        layout.prop(self, "collection_color")
        layout.prop_search(self, "parent_collection_name", bpy.data, "collections")


def add_export_collections_to_menu(self, context):
    """Adds the Simple Export create export collections operator to the object context menu."""
    self.layout.separator()
    op = self.layout.operator("simple_export.create_export_collections", icon='COLLECTION_COLOR_01')
    op.overwrite_collection_name = ""
    op.use_numbering = False


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
