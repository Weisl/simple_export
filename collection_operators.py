import bpy
import os

from .operators import generate_export_path, assign_exporter_path
from .operators import set_active_layer_Collection
from .panels import EXPORT_FORMATS
from .presets import assign_preset


def generate_collection_name(context, obj_name):
    # Construct the export file name
    collection_name = obj_name

    prefs = bpy.context.preferences.addons[__package__].preferences
    wm = context.window_manager
    settings_col = wm if wm.overwrite_collection_settings else prefs

    if getattr(settings_col, 'use_blend_file_name_as_prefix'):
        blend_file_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        if not collection_name.startswith(blend_file_name):
            collection_name = blend_file_name + "_" + collection_name

    prefix = getattr(settings_col, 'custom_prefix')
    suffix = getattr(settings_col, 'custom_suffix')

    if prefix and not collection_name.startswith(prefix):
        collection_name = prefix + "_" + collection_name

    if suffix and not collection_name.endswith(suffix):
        collection_name = collection_name + "_" + suffix

    return collection_name


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
        wm = context.window_manager
        settings_col = wm if wm.overwrite_collection_settings else prefs
        settings_filepath = wm if wm.overwrite_filepath_settings else prefs

        props = context.scene.simple_export_props

        # Check for active object
        if not active_object:
            self.report({'WARNING'}, "No active object selected.")
            return {'CANCELLED'}

        # Ensure parent_collection is a valid bpy.types.Collection
        if not isinstance(parent_collection, bpy.types.Collection):
            self.report({'WARNING'}, "No valid parent collection selected. Falling back to the scene collection.")
            parent_collection = context.scene.collection

        collection_name = generate_collection_name(context, active_object.name)
        # Ensure export collection does not yet exist.
        if collection_name in bpy.data.collections:
            self.report({'WARNING'}, "Collection already exists")
            return {'CANCELLED'}

        # Make sure that blend file exists to retrieve the file path
        if not getattr(settings_filepath, 'use_custom_export_folder') and getattr(settings_col, 'auto_set_filepath'):
            blend_filepath = bpy.data.filepath
            # Return if Blend File hasn't been saved
            if not blend_filepath:
                self.report({'ERROR'}, f"Save the Blend file before calling this operator.")
                return {'CANCELLED'}
            blend_dir = os.path.dirname(blend_filepath)
        elif getattr(settings_filepath, 'custom_export_path'):
            blend_dir = getattr(settings_filepath, 'custom_export_path')

        # Assign the preset
        if getattr(settings_col, 'auto_set_preset'):
            preset_path = props.simple_export_preset_file

            if not preset_path:
                self.report({'ERROR'}, f"No Preset specified.")
                return {'CANCELLED'}

        # Helper function to create or retrieve an existing collection
        def make_collection(col_name, prnt_collection):
            """
            Return existing collection if it exists, otherwise create a new one
            """
            if col_name in bpy.data.collections:
                collect = bpy.data.collections[col_name]
            else:
                collect = bpy.data.collections.new(col_name)
                if collect.name not in prnt_collection.children.keys():
                    prnt_collection.children.link(collect)
            return collect

        export_collection = make_collection(collection_name, parent_collection)

        # assign properties
        export_collection['simple_export_selected'] = True

        # Recursive function to find all children of an object
        def find_children(parent_object, child_stack):
            """ Recursive function to find all children """
            for obj in bpy.data.objects:
                if obj.parent == parent_object:
                    child_stack.append(obj)
                    find_children(obj, child_stack)
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
        color_tag = getattr(settings_col, 'collection_color')
        export_collection.color_tag = color_tag

        # Set instance offset
        if getattr(settings_col, 'set_location_offset_on_creation'):
            export_collection.instance_offset = active_object.location

        # TODO: Set collection offset Object

        if not export_collection:
            self.report({'WARNING'}, "No active collection")
            return {'CANCELLED'}

        # Assign exporter
        # Not sure if this is needed.
        set_active_layer_Collection(collection_name)

        # Assigning the correct format exporter
        export_data = EXPORT_FORMATS.get(props.export_format)

        def get_all_exporters():
            # Replace `bpy.data.` with the appropriate data container for your exporters
            # This is a placeholder, and you should use the correct attribute or structure
            return list(export_collection.exporters)

        exporters_before = get_all_exporters()

        bpy.ops.collection.exporter_add(name=export_data["op_name"])

        exporters_after = get_all_exporters()

        props = context.scene.simple_export_props

        exporter = list(set(exporters_after) - set(exporters_before))[0]

        if getattr(settings_col, 'auto_set_preset'):
            assign_preset(exporter, preset_path)

        if getattr(settings_col, 'auto_set_filepath'):
            search_path = getattr(settings_filepath, 'search_path')
            replacement_path = getattr(settings_filepath, 'replacement_path')

            if not exporter:
                self.report({'ERROR'}, f"Could not add exporter to collection '{collection_name}'.")
                return {'CANCELLED'}

            export_format = props.export_format
            export_path = generate_export_path(collection_name, export_format, blend_dir, search_path, replacement_path)
            success, msg = assign_exporter_path(exporter, export_path)

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
