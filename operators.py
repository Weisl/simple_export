import os

import bpy

from .utils import open_directory, set_active_collection, ensure_export_directory, export_collection


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

    def execute(self, context):
        for collection in bpy.data.collections:
            collection.my_export_select = True
        return {'FINISHED'}


class SCENE_OT_UnselectAllCollections(bpy.types.Operator):
    bl_idname = "scene.unselect_all_collections"
    bl_label = "Unselect All Collections"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for collection in bpy.data.collections:
            collection.my_export_select = False
        return {'FINISHED'}


class SCENE_OT_SetExporterPath(bpy.types.Operator):
    """
    Operator to set the exporter path for a collection based on the original and replacement paths defined in the scene properties.
    """
    bl_idname = "scene.set_exporter_path"
    bl_label = "Set Exporter Path"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        prefs = bpy.context.preferences.addons[__package__].preferences

        collection = bpy.data.collections.get(self.collection_name)
        if not collection:
            self.report({'ERROR'}, f"Collection '{self.collection_name}' not found.")
            return {'CANCELLED'}

        # Path variables
        original_path = prefs.original_path
        replacement_path = prefs.replacement_path

        # Add custom exporter
        exporter = self.get_custom_exporter_for_collection(collection.name, prefs.default_export_format)
        if not exporter:
            self.report({'ERROR'}, f"Could not add exporter to collection '{collection.name}'.")
            return {'CANCELLED'}

        self.set_exporter_path(context, collection.name, exporter, original_path, replacement_path)
        return {'FINISHED'}

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

    def set_exporter_path(self, context, collection_name, exporter, original_path, replacement_path):
        """
        Set the export path for a given collection's exporter.

        Args:
            collection_name (str): The name of the collection.
            exporter (bpy.types.PropertyGroup): The exporter for the collection.
            original_path (str): The original path to be replaced.
            replacement_path (str): The replacement path to be applied.
        """
        prefs = bpy.context.preferences.addons[__package__].preferences

        if prefs.use_blender_file_location:
            blend_filepath = bpy.data.filepath
            if not blend_filepath:
                self.report({'ERROR'}, "Save the Blender file before running the script.")
                return
            export_dir = os.path.dirname(blend_filepath)
        else:
            export_dir = prefs.custom_export_path

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

        ensure_export_directory(exporter)
        exporter.export_properties.filepath = export_path


class SCENE_OT_ExportCollection(bpy.types.Operator):
    """
     Operator to export a single collection.
     """

    bl_idname = "scene.export_collection"
    bl_label = "Export Collection"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if not collection or len(collection.exporters) == 0:
            self.report({'WARNING'}, f"No valid exporter found for collection '{self.collection_name}'.")
            return {'CANCELLED'}

        export_collection(collection, context)

        self.report({'INFO'}, f"Exported collection '{self.collection_name}'.")
        return {'FINISHED'}


class SCENE_OT_ExportSelectedCollections(bpy.types.Operator):
    """
    Operator to export only the collections that have been selected by the user.
    """

    bl_idname = "scene.export_selected_collections"
    bl_label = "Export Collections"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        for collection in bpy.data.collections:
            if not collection.my_export_select or len(collection.exporters) == 0:
                continue

            export_collection(collection, context)
            self.report({'INFO'}, f"Exported collection '{collection.name}'.")

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
            self.report({'WARNING'}, f"Directory does not exist: {export_dir}")
            return {'CANCELLED'}

        open_directory(export_dir)
        self.report({'INFO'}, f"Opened directory: {export_dir}")
        return {'FINISHED'}
