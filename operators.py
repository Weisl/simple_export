import os

import bpy

from .functions import open_directory, ensure_export_folder_exists, export_collection, apply_collection_offset
from .collection_utils import update_collection_offset
from .panels import EXPORT_FORMATS
def recursiceLayerCollection(layerColl, collName):
    # print(f"Checking collection: {layerColl.name}")  # Debug print
    if layerColl.name == collName:
        # print(f"Found collection: {collName}")  # Debug print
        return layerColl
    for layer in layerColl.children:
        found = recursiceLayerCollection(layer, collName)
        if found:
            return found
    return None


def set_active_layer_Collection(collection_name):
    # Switching active Collection to active Object selected
    layer_collection = bpy.context.view_layer.layer_collection
    layerColl = recursiceLayerCollection(layer_collection, collection_name)
    bpy.context.view_layer.active_layer_collection = layerColl


def generate_export_path(collection_name, export_dir, original_path, replacement_path):
    """
    Set the export path for a given collection's exporter.

    Args:
        collection_name (str): The name of the collection.
        exporter_dir (str): Path to the export folder.
        original_path (str): The original path to be replaced.
        replacement_path (str): The replacement path to be applied.
    """
    prefs = bpy.context.preferences.addons[__package__].preferences

    # Construct the export file name
    export_name = ""

    if prefs.use_blend_file_name_as_prefix:
        blend_file_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        export_name += blend_file_name + "_"

    if prefs.custom_prefix:
        export_name += prefs.custom_prefix + "_"

    export_name += collection_name

    if prefs.custom_suffix:
        export_name += "_" + prefs.custom_suffix

    export_name += ".fbx"  # or use prefs.export_format to determine extension
    export_path = os.path.join(export_dir, export_name)

    if original_path in export_path:
        export_path = export_path.replace(original_path, replacement_path)
    return export_path


def assign_exporter_path(exporter, export_path):
    ensure_export_folder_exists(export_path)
    exporter.export_properties.filepath = export_path
    return export_path


def temporarily_disable_offset_handler():
    """Temporarily removes the collection offset update handler."""
    if update_collection_offset in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_collection_offset)


def reenable_offset_handler():
    """Re-enables the collection offset update handler."""
    if update_collection_offset not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(update_collection_offset)

# Popup to show export results
class SCENE_OT_ExportResultsPopup(bpy.types.Operator):
    bl_idname = "scene.export_results_popup"
    bl_label = "Export Results"
    bl_ui_units_x = 50

    export_results: bpy.props.StringProperty()  # JSON-like string to hold results

    def execute(self, context):
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.label(text="Export Results:")

        # Parse export results from JSON-like string
        results = eval(self.export_results)  # Safe since we control input
        for result in results:
            row = layout.row()
            icon = 'CHECKMARK' if result['success'] else 'CANCEL'
            row.label(text=f"{result['name']}: {result['message']}", icon=icon)


class SCENE_OT_CreateExportDirectory(bpy.types.Operator):
    bl_idname = "scene.create_export_directory"
    bl_label = "Create Export Directory"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene

        collection = bpy.data.collections[scene.collection_index]
        if self.collection_name:
            collection = bpy.data.collections.get(self.collection_name)

        if not collection or len(collection.exporters) == 0:
            self.report({'WARNING'}, "No valid exporter found for the active collection.")
            return {'CANCELLED'}

        exporter = collection.exporters[0]
        export_path = exporter.export_properties.filepath
        export_dir = os.path.dirname(export_path)

        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
            self.report({'INFO'}, f"Created directory: {export_dir}")
        else:
            open_directory(export_dir)
            self.report({'INFO'}, f"Opened directory: {export_dir}")

        return {'FINISHED'}


class SCENE_OT_SelectAllCollections(bpy.types.Operator):
    bl_idname = "scene.select_all_collections"
    bl_label = "Select All Collections"
    bl_options = {'REGISTER', 'UNDO'}

    invert: bpy.props.BoolProperty()

    def execute(self, context):
        for collection in bpy.data.collections:
            collection.simple_export_selected = not self.invert
        return {'FINISHED'}


class SCENE_OT_SetExporterPath(bpy.types.Operator):
    """
    Operator to set the exporter path for a collection based on the original and replacement paths defined in the scene properties.
    """
    bl_idname = "scene.set_export_path"
    bl_label = "Set Export Path"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        prefs = bpy.context.preferences.addons[__package__].preferences
        collection = bpy.data.collections.get(self.collection_name)

        prefs = bpy.context.preferences.addons[__package__].preferences

        if prefs.use_blender_file_location:
            blend_filepath = bpy.data.filepath
            # Return if Blend File hasn't been saved
            if not blend_filepath:
                self.report({'ERROR'}, f"Save the Blend file before calling this operator.")
                return {'CANCELLED'}
            export_dir = os.path.dirname(blend_filepath)
        else:
            export_dir = prefs.custom_export_path

        # Return if collection not found
        if not collection:
            self.report({'ERROR'}, f"Collection '{self.collection_name}' not found.")
            return {'CANCELLED'}

        # Path variables
        original_path = prefs.original_path
        replacement_path = prefs.replacement_path
        default_export_format = prefs.default_export_format

        # Add custom exporter
        exporter = self.get_custom_exporter_for_collection(collection.name, default_export_format)

        # Return
        if not exporter:
            self.report({'ERROR'}, f"Could not add exporter to collection '{collection.name}'.")
            return {'CANCELLED'}

        # Set export Path
        export_path = generate_export_path(collection.name, export_dir, original_path, replacement_path)
        export_path = assign_exporter_path(exporter, export_path)

        self.report({'INFO'}, f"Export path set to {export_path}")
        return {'FINISHED'}

    # TODO: improve finding custom exporters
    def get_custom_exporter_for_collection(self, collection_name, exporter_name):
        """
        Retrieve the custom exporter for a given collection.

        Args:
            collection_name (str): The name of the collection.
            exporter_name (str): The name of the exporter.

        Returns:
            bpy.types.PropertyGroup or None: The exporter if found, otherwise None.
        """
        collection = bpy.data.collections.get(collection_name)
        if not collection:
            return None

        for exporter in collection.exporters:
            if exporter.name == exporter_name:
                return exporter

        return None


class SCENE_OT_ExportCollection(bpy.types.Operator):
    """
     Operator to export a single collection.
     """

    bl_idname = "scene.export_collection"
    bl_label = "Export Collection"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty()

    def cancel(self, context):
        reenable_offset_handler()
        return {'CANCELLED'}

    def execute(self, context):
        # Disable offset handler if exporter is active
        temporarily_disable_offset_handler()
        prefs = bpy.context.preferences.addons[__package__].preferences

        # TODO: extract to function - Validate Collection
        collection_name = self.collection_name
        if not collection_name or not bpy.data.collections.get(collection_name):
            self.report({'ERROR'}, f"Invalid export collection.")
            return self.cancel()

        export_collection = bpy.data.collections.get(collection_name)
        set_active_layer_Collection(export_collection.name)

        # TODO: extract to function - Validate Exporter
        if len(export_collection.exporters) == 0:
            self.report({'ERROR'}, f"No exporter found for collection '{collection_name}'.")
            return self.cancel()

        # Validate exporter type
        props = context.scene.simple_export_props
        export_format = props.export_format
        exporter = None


        # find exporter
        for exp in export_collection.exporters:
            if type(exp) == EXPORT_FORMATS[export_format]["op_type"]:
                exporter = exp

        if exporter == None:
            self.report({'ERROR'}, f"No {export_format} exporter found for collection {collection_name}'.")
            return self.cancel()

        # find exporter id
        exporter_id = -1
        for idx, exp in enumerate(export_collection.exporters):
            if exp is exporter:
                exporter_id = idx

        if exporter_id == -1:
            self.report({'ERROR'}, f" {exporter.name} not found in the exporters of collection {collection_name}'.")
            return self.cancel()


        #TODO: extract to function - Validate Export path
        export_path = exporter.export_properties.filepath
        print(f'Exporter Path: {export_path}')
        # Ensure the export directory exists
        ensure_export_folder_exists(export_path)

        # export
        export_results = []  # Store results

        # Apply instance offset if the preference is enabled
        if prefs.use_instance_offset:
            apply_collection_offset(export_collection)

        try:
            bpy.ops.collection.exporter_export(index=exporter_id)
        except Exception as e:
            self.report({'ERROR'}, f" {exporter.name} not found in the exporters of collection {collection_name}'.")
            apply_collection_offset(export_collection, inverse=True)
            return self.cancel()


        apply_collection_offset(export_collection, inverse=True)
        # Create and invoke the popup operator instance
        # bpy.ops.scene.export_results_popup('INVOKE_DEFAULT', export_results=str(export_results))

        return {'FINISHED'}


# Operator to export selected collections
class SCENE_OT_ExportSelectedCollections(bpy.types.Operator):
    bl_idname = "scene.export_selected_collections"
    bl_label = "Export Selected Collections"
    bl_options = {'REGISTER', 'UNDO'}


    def execute(self, context):
        print('TODO')
        return {'FINISHED'}


class SCENE_OT_OpenExportDirectory(bpy.types.Operator):
    """
    Operator to open the export directory of the currently selected collection in the file explorer.
    """
    bl_idname = "scene.open_export_directory"
    bl_label = "Open Export Directory"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if not collection or len(collection.exporters) == 0:
            self.report({'WARNING'}, "No valid exporter found for the active collection.")
            return {'CANCELLED'}

        exporter = collection.exporters[0]
        export_path = exporter.export_properties.filepath
        export_dir = os.path.dirname(export_path)

        if not os.path.exists(export_dir):
            self.report({'WARNING'}, f"Directory does not exist: {export_dir}")
            return {'CANCELLED'}

        open_directory(export_dir)
        self.report({'INFO'}, f"Opened directory: {export_dir}")
        return {'FINISHED'}


classes = (SCENE_OT_CreateExportDirectory,
           SCENE_OT_ExportResultsPopup,
           SCENE_OT_SelectAllCollections,
           SCENE_OT_SetExporterPath,
           SCENE_OT_ExportCollection,
           SCENE_OT_ExportSelectedCollections,
           SCENE_OT_OpenExportDirectory,)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
