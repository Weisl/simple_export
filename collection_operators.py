import os

import bpy

from .operators import generate_export_path, assign_exporter_path
from .operators import set_active_layer_Collection
from .panels import EXPORT_FORMATS
from .presets import assign_preset


class EXPORT_OT_CreateExportCollection(bpy.types.Operator):
    """
    Create a new collection for the active object and its children.
    """
    bl_idname = "simple_export.create_export_collection"
    bl_label = "Create Export Collection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active_object = context.active_object
        parent_collection = context.scene.parent_collection or context.scene.collection
        prefs = bpy.context.preferences.addons[__package__].preferences

        # Check for active object
        if not active_object:
            self.report({'WARNING'}, "No active object selected.")
            return {'CANCELLED'}

        # Ensure parent_collection is a valid bpy.types.Collection
        if not isinstance(parent_collection, bpy.types.Collection):
            self.report({'WARNING'}, "No valid parent collection selected. Falling back to the scene collection.")
            parent_collection = context.scene.collection

        # Ensure export collection does not yet exist.
        if active_object.name in bpy.data.collections:
            self.report({'WARNING'}, "Collection already exists")
            return {'CANCELLED'}

        # Make sure that blend file exists to retrieve the file path
        if prefs.use_blender_file_location:
            blend_filepath = bpy.data.filepath
            # Return if Blend File hasn't been saved
            if not blend_filepath:
                self.report({'ERROR'}, f"Save the Blend file before calling this operator.")
                return {'CANCELLED'}
            export_dir = os.path.dirname(blend_filepath)
        else:
            export_dir = prefs.custom_export_path

        # Helper function to create or retrieve an existing collection
        def make_collection(collection_name, parent_collection):
            """
            Return existing collection if it exists, otherwise create a new one
            """
            if collection_name in bpy.data.collections:
                col = bpy.data.collections[collection_name]
            else:
                col = bpy.data.collections.new(collection_name)
                if col.name not in parent_collection.children.keys():
                    parent_collection.children.link(col)
            return col

        # Create or get the export collection
        collection_name = active_object.name
        export_collection = make_collection(collection_name, parent_collection)

        # Recursive function to find all children of an object
        def find_children(parent_object, child_stack):
            """ Recursive function to find all children """
            for ob in bpy.data.objects:
                if ob.parent == parent_object:
                    child_stack.append(ob)
                    find_children(ob, child_stack)
            return child_stack

        # Find all children of the active object
        collection_objects = find_children(active_object, [])
        collection_objects.append(active_object)  # Add the active object itself

        # Link objects to the new collection
        for ob in collection_objects:
            # Avoid redundant linking
            if export_collection not in ob.users_collection:
                export_collection.objects.link(ob)

            # Unlink the object from other collections
            for col in ob.users_collection:
                if col != export_collection:
                    col.objects.unlink(ob)

        # Set collection Color:
        color_tag = prefs.collection_color
        export_collection.color_tag = color_tag

        # Set instance offset
        if prefs.set_location_offset_on_creation:
            export_collection.instance_offset = active_object.location

        # TODO: Set collection offset Object

        if not export_collection:
            self.report({'WARNING'}, "No active collection")
            return {'CANCELLED'}

        # Assign exporter
        # Not sure if this is needed.
        set_active_layer_Collection(collection_name)

        # Assigning the correct format exporter
        props = context.scene.simple_export_props
        export_data = EXPORT_FORMATS.get(props.export_format)

        def get_all_exporters():
            # Replace `bpy.data.` with the appropriate data container for your exporters
            # This is a placeholder, and you should use the correct attribute or structure
            return list(export_collection.exporters)

        exporters_before = get_all_exporters()

        bpy.ops.collection.exporter_add(name=export_data["op_name"])

        exporters_after = get_all_exporters()

        exporter = list(set(exporters_after) - set(exporters_before))[0]

        props = context.scene.simple_export_props
        # Assign the preset
        if prefs.auto_set_preset:
            preset_path = props.simple_export_preset_file

            if preset_path:
                assign_preset(export_collection, preset_path)
            else:
                self.report({'WARNING'}, f"No Preset.")

        if prefs.auto_set_filepath:
            original_path = prefs.original_path
            replacement_path = prefs.replacement_path

            if not exporter:
                self.report({'ERROR'}, f"Could not add exporter to collection '{collection_name}'.")
                return {'CANCELLED'}

            export_path = generate_export_path(collection_name, export_dir, original_path, replacement_path)
            export_path = assign_exporter_path(exporter, export_path)

        self.report({'INFO'}, f"Export collection '{export_collection.name}' created successfully.")
        return {'FINISHED'}


classes = (
    EXPORT_OT_CreateExportCollection,
)


# Register the scene property
def register():
    from bpy.utils import register_class
    Scene = bpy.types.Scene
    Scene.parent_collection = bpy.props.PointerProperty(
        name="Parent Collection",
        description="Choose the parent collection to link the new collection to",
        type=bpy.types.Collection
    )
    Scene.set_filepath_on_creation = bpy.props.BoolProperty(
        name="Set Filepath",
        description="Set filepath based on blend file location",
    )
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    Scene = bpy.types.Scene

    for cls in reversed(classes):
        unregister_class(cls)

    del Scene.parent_collection
    del Scene.set_filepath_on_creation
