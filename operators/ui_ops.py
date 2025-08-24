import bpy
import os

from ..functions.exporter_funcs import find_exporter
from ..functions.path_utils import clean_relative_path


class SIMPLE_OT_OpenCollectionExporterProperties(bpy.types.Operator):
    """Go to the selected collection's properties and focus on the exporter"""
    bl_idname = "simple_export.open_exporter_in_properties"
    bl_label = "Open Exporter Properties"
    bl_description = "Open the properties of the selected collection and focus on the exporter settings."
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    collection_name: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        # Get the selected collection
        collection = bpy.data.collections.get(self.collection_name)
        if not collection:
            self.report({'WARNING'}, f"Collection '{self.collection_name}' not found.")
            return {'CANCELLED'}

        # Find the corresponding LayerCollection
        def find_layer_collection(layer_collection, collection):
            if layer_collection.collection == collection:
                return layer_collection
            for child in layer_collection.children:
                found = find_layer_collection(child, collection)
                if found:
                    return found
            return None

        layer_collection = find_layer_collection(context.view_layer.layer_collection, collection)
        if not layer_collection:
            self.report({'ERROR'}, f"LayerCollection for '{collection.name}' not found.")
            return {'CANCELLED'}

        # Ensure a properties editor is open and set the correct context
        for area in context.screen.areas:
            if area.type == 'PROPERTIES':
                for space in area.spaces:
                    if space.type == 'PROPERTIES':
                        space.context = 'COLLECTION'
                        context.view_layer.active_layer_collection = layer_collection
                        break
                break
        else:
            self.report({'ERROR'}, "No properties editor found. Please open one manually.")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Focused on Collection: {collection.name}")
        return {'FINISHED'}


class SCENE_OT_SelectAllCollections(bpy.types.Operator):
    bl_idname = "scene.select_all_collections"
    bl_label = "Select All Collections"
    bl_description = "Select or deselect all collections for export."
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    deselect: bpy.props.BoolProperty(name="Invert", default=False, )

    def execute(self, context):
        for collection in bpy.data.collections:
            collection.simple_export_selected = not self.deselect
        return {'FINISHED'}


class SCENE_OT_OpenExportDirectory(bpy.types.Operator):
    """
    Operator to open the export directory of the currently selected collection in the file explorer.
    """
    bl_idname = "scene.open_export_directory"
    bl_label = "Open Export Directory"
    bl_description = "Open the export directory of the currently selected collection in the file explorer."
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    collection_name: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if not collection or len(collection.exporters) == 0:
            self.report({'WARNING'}, "No valid exporter found for the active collection.")
            return {'CANCELLED'}

        scene = context.scene
        exporter = find_exporter(collection, format_filter=scene.export_format)
        export_path = exporter.export_properties.filepath
        export_dir = os.path.dirname(export_path)
        export_dir = clean_relative_path(os.path.dirname(export_dir))

        if not os.path.exists(export_dir):
            self.report({'WARNING'}, f"Directory does not exist: {export_dir}")
            return {'CANCELLED'}

        bpy.ops.file.external_operation(filepath=export_dir, operation='FOLDER_OPEN')
        self.report({'INFO'}, f"Opened directory: {export_dir}")
        return {'FINISHED'}


classes = (
    SCENE_OT_SelectAllCollections,
    SCENE_OT_OpenExportDirectory,
    SIMPLE_OT_OpenCollectionExporterProperties,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
