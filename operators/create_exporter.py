import bpy

from .. import __package__ as base_package
from ..functions.create_collection_func import generate_base_name, setup_collection


import bpy
from .. import __package__ as base_package
from ..functions.create_collection_func import generate_base_name, setup_collection

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

    individual_collections: bpy.props.BoolProperty(
        name="Individual Collections",
        description="Create individual collections for each object with numbering",
        default=True
    )

    is_adjusted: bpy.props.BoolProperty(
        default=False,
        options={'HIDDEN'}
    )

    def invoke(self, context, event):
        # Reset the overwrite_collection_name property only if not adjusted
        if not self.is_adjusted:
            self.overwrite_collection_name = ""
        self.is_adjusted = False
        return self.execute(context)

    def execute(self, context):
        selected_objects = context.selected_objects

        if not selected_objects:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}

        # Get preferences and settings
        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene

        settings_col = scene if scene.overwrite_collection_settings else prefs
        settings_filepath = scene if scene.overwrite_filepath_settings else prefs
        settings_filename = scene if scene.overwrite_filename_settings else prefs

        prefix = getattr(settings_col, 'collection_custom_prefix', '')
        suffix = getattr(settings_col, 'collection_custom_suffix', '')

        if self.individual_collections:
            # Create individual collections for each object
            for index, top_object in enumerate(selected_objects):
                if not top_object.parent or top_object.parent not in selected_objects:
                    padded_index = f"{index:03}"
                    collection_name = f"{self.overwrite_collection_name}_{padded_index}" if self.overwrite_collection_name else generate_base_name(
                        top_object.name, prefix, suffix, getattr(settings_col, 'collection_file_name_prefix', '')
                    )

                    # Create a new collection
                    export_collection = bpy.data.collections.new(collection_name)
                    context.scene.collection.children.link(export_collection)

                    objects = selected_objects if self.only_selection else bpy.data.objects
                    hierarchy_objects = self.collect_children(top_object, objects)

                    for obj in hierarchy_objects:
                        if export_collection not in obj.users_collection:
                            export_collection.objects.link(obj)
                        for col in obj.users_collection:
                            if col != export_collection:
                                col.objects.unlink(obj)

                    setup_collection(context, export_collection, top_object, settings_col, settings_filepath, settings_filename)
                    self.report({'INFO'}, f"Export collection '{export_collection.name}' created successfully for '{top_object.name}'.")

        else:
            # Create a single collection for all objects
            collection_name = self.overwrite_collection_name if self.overwrite_collection_name else "Combined_Collection"

            # Check if the collection already exists, but don't cancel the operation
            if collection_name in bpy.data.collections:
                export_collection = bpy.data.collections[collection_name]
                self.report({'WARNING'}, f"Collection '{collection_name}' already exists. Using existing collection.")
            else:
                export_collection = bpy.data.collections.new(collection_name)
                context.scene.collection.children.link(export_collection)

            for top_object in selected_objects:
                if not top_object.parent or top_object.parent not in selected_objects:
                    objects = selected_objects if self.only_selection else bpy.data.objects
                    hierarchy_objects = self.collect_children(top_object, objects)

                    for obj in hierarchy_objects:
                        if export_collection not in obj.users_collection:
                            export_collection.objects.link(obj)
                        for col in obj.users_collection:
                            if col != export_collection:
                                col.objects.unlink(obj)

            setup_collection(context, export_collection, None, settings_col, settings_filepath, settings_filename)
            self.report({'INFO'}, f"Export collection '{export_collection.name}' created successfully for all objects.")

        return {'FINISHED'}

    def collect_children(self, obj, objects):
        children = [child for child in objects if child.parent == obj]
        return [obj] + [child for child in children]

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "overwrite_collection_name")
        layout.prop(self, "individual_collections")

    def modal(self, context, event):
        # This method is not strictly necessary unless you have modal operations
        # It's included here to demonstrate where you might handle adjustments
        return {'FINISHED'}


def add_export_collections_to_menu(self, context):
    """Adds the Simple Export create export collections operator to the object context menu."""
    self.layout.separator()
    op = self.layout.operator("simple_export.create_export_collections", icon='COLLECTION_COLOR_01')
    op.overwrite_collection_name = ""


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
