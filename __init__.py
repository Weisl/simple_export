bl_info = {
    "name": "Custom Collection Exporter",
    "blender": (4, 2, 0),
    "category": "Scene",
}

import bpy
import os
import subprocess
import platform


# Operator to set the exporter path based on the provided script
class SCENE_OT_SetExporterPath(bpy.types.Operator):
    bl_idname = "scene.set_exporter_path"
    bl_label = "Set Exporter Path"

    def execute(self, context):
        scene = context.scene
        collection = bpy.data.collections[scene.collection_index]
        original_path = scene.original_path
        replacement_path = scene.replacement_path

        if collection:
            exporter_name = "FBX"
            exporter = self.add_custom_exporter_to_collection(collection.name, exporter_name)
            if exporter:
                self.set_exporter_path(collection.name, exporter, original_path, replacement_path)
        return {'FINISHED'}

    def add_custom_exporter_to_collection(self, collection_name, exporter_name):
        # Get the collection
        collection = bpy.data.collections.get(collection_name)
        if not collection:
            print(f"Error: Collection '{collection_name}' not found.")
            return None

        # Check if the custom exporter property already exists
        for exporter in collection.exporters:
            if exporter.name == exporter_name:
                print(f"Custom exporter '{exporter_name}' already exists in the collection.")
                return exporter
        return None

    def set_exporter_path(self, collection_name, exporter, original_path, replacement_path):
        # Get the current Blender file directory
        blend_filepath = bpy.data.filepath
        blend_dir = os.path.dirname(blend_filepath)

        # Ensure the Blender file is saved
        if not blend_filepath:
            self.report({'ERROR'}, "Save the Blender file before running the script.")
            return

        # Create the export path with the collection name as the file name
        export_name = collection_name + ".fbx"
        export_path = os.path.join(blend_dir, export_name)

        # Replace part of the path if original_path is found
        if original_path in export_path:
            export_path = export_path.replace(original_path, replacement_path)

        # Ensure the directory exists, create if not
        export_dir = os.path.dirname(export_path)
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)
            print(f"Created directory: {export_dir}")

        exporter.export_properties.filepath = export_path

        # Print the export path for debugging
        print(f"Set export path to: {export_path}")


class SCENE_OT_ExportCollection(bpy.types.Operator):
    bl_idname = "scene.export_collection"
    bl_label = "Export Collection"

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if collection and len(collection.exporters) > 0:
            # Set the collection as the active collection
            layer_collection = bpy.context.view_layer.layer_collection
            for layer in layer_collection.children:
                if layer.name == collection.name:
                    bpy.context.view_layer.active_layer_collection = layer
                    break

            # Get the export path and ensure the directory exists
            exporter = collection.exporters[0]
            export_path = exporter.export_properties.filepath
            export_dir = os.path.dirname(export_path)
            if not os.path.exists(export_dir):
                os.makedirs(export_dir)
                self.report({'INFO'}, f"Created directory: {export_dir}")

            # Use the Blender 4.2 method to export the collection
            bpy.ops.collection.exporter_export(index=0)
            self.report({'INFO'}, f"Exported collection '{self.collection_name}' to {export_path}")
        else:
            self.report({'WARNING'}, f"No valid exporter found for collection '{self.collection_name}'")
        return {'FINISHED'}


class SCENE_OT_ExportAllCollections(bpy.types.Operator):
    bl_idname = "scene.export_all_collections"
    bl_label = "Export All Collections"

    def execute(self, context):
        for collection in bpy.data.collections:
            if len(collection.exporters) > 0:
                # Set the collection as the active collection
                layer_collection = bpy.context.view_layer.layer_collection
                for layer in layer_collection.children:
                    if layer.name == collection.name:
                        bpy.context.view_layer.active_layer_collection = layer
                        break

                # Get the export path and ensure the directory exists
                exporter = collection.exporters[0]
                export_path = exporter.export_properties.filepath
                export_dir = os.path.dirname(export_path)
                if not os.path.exists(export_dir):
                    os.makedirs(export_dir)
                    self.report({'INFO'}, f"Created directory: {export_dir}")

                # Use the Blender 4.2 method to export the collection
                bpy.ops.collection.exporter_export(index=0)
                self.report({'INFO'}, f"Exported collection '{collection.name}' to {export_path}")
        return {'FINISHED'}


class SCENE_OT_OpenExportDirectory(bpy.types.Operator):
    bl_idname = "scene.open_export_directory"
    bl_label = "Open Export Directory"

    def execute(self, context):
        scene = context.scene
        collection = bpy.data.collections[scene.collection_index]

        if collection and len(collection.exporters) > 0:
            exporter = collection.exporters[0]
            export_path = exporter.export_properties.filepath
            export_dir = os.path.dirname(export_path)

            if os.path.exists(export_dir):
                if platform.system() == "Windows":
                    subprocess.Popen(f'explorer "{export_dir}"')
                elif platform.system() == "Darwin":
                    subprocess.Popen(["open", export_dir])
                else:  # Linux and other platforms
                    subprocess.Popen(["xdg-open", export_dir])
                self.report({'INFO'}, f"Opened directory: {export_dir}")
            else:
                self.report({'WARNING'}, f"Directory does not exist: {export_dir}")
        else:
            self.report({'WARNING'}, "No valid exporter found for the active collection.")
        return {'FINISHED'}


# UI List of all collections with an exporter
class SCENE_UL_CollectionList(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        collection = item
        if collection:
            row = layout.row()
            row.label(text=collection.name, icon='OUTLINER_COLLECTION')

            # Assuming the first exporter is being shown (customize as needed)
            if len(collection.exporters) > 0:
                exporter = collection.exporters[0]
                row.label(text=exporter.export_properties.filepath)

                # Add export button for each collection
                op = row.operator("scene.export_collection", text="", icon='EXPORT')
                op.collection_name = collection.name

    def filter_items(self, context, data, propname):
        flt_flags = []
        flt_neworder = []

        for i, collection in enumerate(bpy.data.collections):
            # Check if the collection has exporters
            if len(collection.exporters) > 0:
                flt_flags.append(self.bitflag_filter_item)
            else:
                flt_flags.append(0)

        return flt_flags, flt_neworder


class SCENE_PT_CollectionExportPanel(bpy.types.Panel):
    bl_label = "Collection Exporter"
    bl_idname = "SCENE_PT_collection_export_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Draw the collection list
        row = layout.row()
        row.template_list("SCENE_UL_CollectionList", "", bpy.data, "collections", scene, "collection_index")

        # Draw string inputs for Original Path and Replacement Path
        layout.prop(scene, "original_path")
        layout.prop(scene, "replacement_path")

        # Draw button to set exporter path
        layout.operator("scene.set_exporter_path", text="Set Exporter Path")

        # Draw button to export all collections
        layout.operator("scene.export_all_collections", text="Export All Collections")

        # Draw button to open the export directory
        layout.operator("scene.open_export_directory", text="Open Export Directory")


# Scene properties to define original_path and replacement_path
def register_scene_properties():
    bpy.types.Scene.original_path = bpy.props.StringProperty(
        name="Original Path",
        description="The path to be replaced.",
        default="workdata"
    )
    bpy.types.Scene.replacement_path = bpy.props.StringProperty(
        name="Replacement Path",
        description="The path to replace with.",
        default="sourcedata"
    )
    bpy.types.Scene.collection_index = bpy.props.IntProperty(
        name="Collection Index",
        description="Index of the active collection in the list",
        default=0
    )


def unregister_scene_properties():
    del bpy.types.Scene.original_path
    del bpy.types.Scene.replacement_path
    del bpy.types.Scene.collection_index


# Register and Unregister classes
classes = (
    SCENE_OT_SetExporterPath,
    SCENE_OT_ExportCollection,
    SCENE_OT_ExportAllCollections,
    SCENE_OT_OpenExportDirectory,
    SCENE_UL_CollectionList,
    SCENE_PT_CollectionExportPanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_scene_properties()


def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    unregister_scene_properties()


if __name__ == "__main__":
    register()
