import bpy

from .. import __package__ as base_package
from ..functions.create_collection_func import generate_base_name, setup_collection


class EXPORT_OT_CreateExportCollections(bpy.types.Operator):
    """
    Create a new collection for each selected object and its children, preserving hierarchy.
    This operator ensures that each top-level selected object and its children are placed in a new collection.
    """

    bl_idname = "simple_export.create_export_collections"
    bl_label = "Create Export Collections"
    bl_options = {'REGISTER', 'UNDO'}

    only_selection: bpy.props.BoolProperty(
        name="Only affect selection",
        description="Only affect selected objects",
        default=False,
        options={'HIDDEN'}
    )

    overwrite_collection_name: bpy.props.StringProperty(
        name="Overwrite Collection Name",
        description="Overwrite the name for the newly created export collection",
        default=""
    )

    use_numbering: bpy.props.BoolProperty(
        name="Use Numbering",
        description="Add numbered suffix to collection names",
        default=True
    )

    def execute(self, context):
        selected_objects = context.selected_objects
        parent_collection = context.scene.parent_collection

        # Get preferences and settings
        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene

        settings_col = scene if scene.overwrite_collection_settings else prefs
        settings_filepath = scene if scene.overwrite_filepath_settings else prefs
        settings_filename = scene if scene.overwrite_filename_settings else prefs

        if not selected_objects:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}

        # Identify top-level objects (objects without a selected parent)
        top_level_objects = [obj for obj in selected_objects if not obj.parent or obj.parent not in selected_objects]

        prefix = getattr(settings_col, 'collection_custom_prefix', '')
        suffix = getattr(settings_col, 'collection_custom_suffix', '')

        for index, top_object in enumerate(top_level_objects):
            # Generate a padded index string if numbering is enabled
            padded_index = f"{index:03}" if self.use_numbering else ""

            # Use the provided collection_name or generate a new one, and append the padded index if applicable
            collection_name = f"{self.overwrite_collection_name}_{padded_index}" if self.overwrite_collection_name else generate_base_name(
                top_object.name, prefix, suffix, getattr(settings_col, 'collection_file_name_prefix', '')
            )

            if collection_name in bpy.data.collections:
                self.report({'WARNING'}, f"Collection '{collection_name}' already exists. Skipping.")
                continue

            # Create a new collection
            export_collection = bpy.data.collections.new(collection_name)

            # Determine the parent collection
            if parent_collection is None:
                if top_object.users_collection:
                    parent_collection = top_object.users_collection[0]
                else:
                    parent_collection = context.scene.collection
                    self.report({'WARNING'},
                                f"No valid parent collection found for object '{top_object.name}'. Falling back to the scene collection.")
            elif not isinstance(parent_collection, bpy.types.Collection):
                self.report({'WARNING'}, "No valid parent collection selected. Falling back to the scene collection.")
                parent_collection = context.scene.collection

            # Link the new collection to the parent collection
            parent_collection.children.link(export_collection)

            # Determine the objects to process
            objects = selected_objects if self.only_selection else bpy.data.objects

            # Recursively collect children of the top-level object
            def collect_children(obj):
                children = [child for child in objects if child.parent == obj]
                return [obj] + [child for child in children]

            hierarchy_objects = collect_children(top_object)

            # Link objects to the new collection and unlink from others
            for obj in hierarchy_objects:
                if export_collection not in obj.users_collection:
                    export_collection.objects.link(obj)
                for col in obj.users_collection:
                    if col != export_collection:
                        col.objects.unlink(obj)

            # Setup the collection with additional settings
            setup_collection(context, export_collection, top_object, settings_col, settings_filepath, settings_filename)

            self.report({'INFO'},
                        f"Export collection '{export_collection.name}' created successfully for '{top_object.name}'.")

        return {'FINISHED'}

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "overwrite_collection_name")
        layout.prop(self, "use_numbering")


def add_export_collections_to_menu(self, context):
    """Adds the Simple Export create export collections operator to the object context menu."""
    self.layout.separator()
    self.layout.operator("simple_export.create_export_collections", icon='COLLECTION_COLOR_01')


classes = (
    EXPORT_OT_CreateExportCollections,
)


# Register the scene property
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
