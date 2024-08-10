bl_info = {
    "name": "Simple Export",
    "blender": (4, 2, 0),
    "category": "Scene",
}

import os
import platform
import subprocess

import bpy


# needed for adding direct link to settings
def get_addon_name():
    """
    Returns the addon name as a string.
    """
    return "Simple Export"


def ensure_export_directory(exporter):
    """
    Ensure the directory for the export path exists, creating it if necessary.

    Args:
        exporter (bpy.types.PropertyGroup): The exporter containing the export path.
    """
    export_path = exporter.export_properties.filepath
    export_dir = os.path.dirname(export_path)
    if export_dir and not os.path.exists(export_dir):
        os.makedirs(export_dir)


def set_active_collection(collection_name):
    """
    Set the given collection as the active collection.

    Args:
        collection_name (str): The name of the collection to set as active.
    """
    layer_collection = bpy.context.view_layer.layer_collection
    for layer in layer_collection.children:
        if layer.name == collection_name:
            bpy.context.view_layer.active_layer_collection = layer
            return


def open_directory(export_dir):
    """
    Open the given directory in the file explorer.

    Args:
        export_dir (str): The directory to open.
    """
    if platform.system() == "Windows":
        subprocess.Popen(f'explorer "{export_dir}"')
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", export_dir])
    else:  # Linux and other platforms
        subprocess.Popen(["xdg-open", export_dir])


class SCENE_OT_CreateExportDirectory(bpy.types.Operator):
    bl_idname = "scene.create_export_directory"
    bl_label = "Create Export Directory"

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

    def execute(self, context):
        for collection in bpy.data.collections:
            collection.my_export_select = True
        return {'FINISHED'}


class SCENE_OT_UnselectAllCollections(bpy.types.Operator):
    bl_idname = "scene.unselect_all_collections"
    bl_label = "Unselect All Collections"

    def execute(self, context):
        for collection in bpy.data.collections:
            collection.my_export_select = False
        return {'FINISHED'}


class CustomExporterPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    show_lock_icons: bpy.props.BoolProperty(
        name="Show Lock Icons",
        description="Show or hide the LOCKED/UNLOCKED icons in the UIList.",
        default=True
    )

    show_edit_icons: bpy.props.BoolProperty(
        name="Show Edit Icons",
        description="Show or hide the EDIT/New icons in the UIList.",
        default=True
    )

    use_blender_file_location: bpy.props.BoolProperty(
        name="Use Blender File Location",
        description="If checked, the export path will be set to the Blender file location. If unchecked, a custom path will be used.",
        default=True
    )

    custom_export_path: bpy.props.StringProperty(
        name="Custom Export Path",
        description="Custom directory to export files to.",
        subtype='DIR_PATH'
    )

    use_blend_file_name_as_prefix: bpy.props.BoolProperty(
        name="Use Blend File Name as Prefix",
        description="If checked, the Blender file name will be used as a prefix for the export file name.",
        default=False
    )

    custom_prefix: bpy.props.StringProperty(
        name="Custom Prefix",
        description="Custom prefix to add to the export file name."
    )

    custom_suffix: bpy.props.StringProperty(
        name="Custom Suffix",
        description="Custom suffix to add to the export file name."
    )

    default_export_format: bpy.props.EnumProperty(
        name="Default Export Format",
        description="Default format for exporting collections.",
        items=[
            ('Universal Scene Description', "USD (.usd)", "Export to USD format"),
            ('Alembic', "Alembic (.abc)", "Export to Alembic format"),
            ('Wavefront OBJ', "OBJ (.obj)", "Export to OBJ format"),
            ('Stanford PLY', "PLY (.ply)", "Export to PLY format"),
            ('STL', "STL (.stl)", "Export to STL format"),
            ('FBX', "FBX (.fbx)", "Export to FBX format"),
            ('glTF 2.0', "glTF (.gltf)", "Export to glTF format"),
        ],
        default='FBX'  # Default value set to FBX
    )

    original_path: bpy.props.StringProperty(
        name="Original Path",
        description="The path to be replaced.",
        default="workdata"
    )
    replacement_path: bpy.props.StringProperty(
        name="Replacement Path",
        description="The path to replace with.",
        default="sourcedata"
    )

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_blender_file_location")
        if not self.use_blender_file_location:
            layout.prop(self, "custom_export_path")
        layout.prop(self, "use_blend_file_name_as_prefix")
        layout.prop(self, "custom_prefix")
        layout.prop(self, "custom_suffix")
        layout.prop(self, "default_export_format")
        layout.prop(self, "show_edit_icons")
        layout.prop(self, "show_lock_icons")



class SCENE_OT_SetExporterPath(bpy.types.Operator):
    """
    Operator to set the exporter path for a collection based on the original and replacement paths defined in the scene properties.
    """
    bl_idname = "scene.set_exporter_path"
    bl_label = "Set Exporter Path"

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        scene = context.scene
        prefs = bpy.context.preferences.addons[__name__].preferences

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
        prefs = bpy.context.preferences.addons[__name__].preferences

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

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if not collection or len(collection.exporters) == 0:
            self.report({'WARNING'}, f"No valid exporter found for collection '{self.collection_name}'.")
            return {'CANCELLED'}

        set_active_collection(collection.name)
        ensure_export_directory(collection.exporters[0])

        bpy.ops.collection.exporter_export(index=0)
        self.report({'INFO'}, f"Exported collection '{self.collection_name}'.")
        return {'FINISHED'}


class SCENE_OT_ExportAllCollections(bpy.types.Operator):
    """
    Operator to export all collections in the scene that have an exporter.
    """

    bl_idname = "scene.export_all_collections"
    bl_label = "Export All Collections"

    def execute(self, context):
        for collection in bpy.data.collections:
            if len(collection.exporters) == 0:
                continue

            set_active_collection(collection.name)
            ensure_export_directory(collection.exporters[0])

            bpy.ops.collection.exporter_export(index=0)
            self.report({'INFO'}, f"Exported collection '{collection.name}'.")

        return {'FINISHED'}


class SCENE_OT_ExportSelectedCollections(bpy.types.Operator):
    """
    Operator to export only the collections that have been selected by the user.
    """

    bl_idname = "scene.export_selected_collections"
    bl_label = "Export Collections"

    def execute(self, context):
        for collection in bpy.data.collections:
            if not collection.my_export_select or len(collection.exporters) == 0:
                continue

            set_active_collection(collection.name)
            ensure_export_directory(collection.exporters[0])
            bpy.ops.collection.exporter_export(index=0)
            self.report({'INFO'}, f"Exported collection '{collection.name}'.")

        return {'FINISHED'}


class SCENE_OT_OpenExportDirectory(bpy.types.Operator):
    """
    Operator to open the export directory of the currently selected collection in the file explorer.
    """
    bl_idname = "scene.open_export_directory"
    bl_label = "Open Export Directory"

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


class SCENE_UL_CollectionList(bpy.types.UIList):
    """
    UIList displaying all collections with an exporter matching the selected export type.
    """

    def draw_filter(self, context, layout):
        layout.prop(context.scene, "export_format", text="Export Format")
        row = layout.row(align=True)
        row.operator("scene.select_all_collections", text="Select All", icon='CHECKBOX_HLT')
        row.operator("scene.unselect_all_collections", text="Unselect All", icon='CHECKBOX_DEHLT')

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        prefs = context.preferences.addons[__package__].preferences
        collection = item
        if not collection:
            return

        row = layout.row(align=True)

        # Checkbox as the first item
        row.prop(collection, "my_export_select", text="")

        exporter = collection.exporters[0]
        export_path = exporter.export_properties.filepath
        file_exists = os.path.exists(export_path)
        is_locked = file_exists and not os.access(export_path, os.W_OK)

        # Conditionally show icons based on preferences
        if prefs.show_lock_icons:
            lock_icon = 'LOCKED' if is_locked else 'UNLOCKED'
            row.label(icon=lock_icon)

        if prefs.show_edit_icons:
            file_icon = 'CURRENT_FILE' if file_exists else 'FILE_NEW'
            row.label(icon=file_icon)

        # Display collection name
        # row.label(text=collection.name, icon='OUTLINER_COLLECTION')
        # Display collection name as a prop
        row.prop(collection, "name", text="", icon='OUTLINER_COLLECTION')

        # Filepath with more space
        row.label(text=export_path)  # Full path as a label
        # row.prop(exporter.export_properties, "filepath", text="", expand=True)  # Filename as editable prop

        # Buttons for setting export path and opening the directory
        op = row.operator("scene.set_exporter_path", text="", icon='FILE_REFRESH')
        op.collection_name = collection.name

        if not file_exists:
            op = row.operator("scene.create_export_directory", text="", icon='FILE_FOLDER')
            op.collection_name = collection.name

        # Add the Export Collection button
        op = row.operator("scene.export_collection", text="", icon='EXPORT')
        op.collection_name = collection.name

    def filter_items(self, context, data, propname):
        flt_flags = []
        flt_neworder = []

        export_format = context.scene.export_format

        for i, collection in enumerate(bpy.data.collections):
            # Filter out collections without exporters or without matching exporters
            has_matching_exporter = any(
                exporter.name == export_format for exporter in collection.exporters
            )

            if has_matching_exporter:
                flt_flags.append(self.bitflag_filter_item)
            else:
                flt_flags.append(0)

        return flt_flags, flt_neworder


# Removed the SCENE_OT_ExportAllCollections class
# Removed "Export All Collections" button from the panel

class SCENE_PT_CollectionExportPanel(bpy.types.Panel):
    bl_label = "Simple Exporter"
    bl_idname = "SCENE_PT_collection_export_panel"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator("wm.url_open", text="", icon='HELP').url = "https://weisl.github.io/exportin/"
        addon_name = get_addon_name()

        op = row.operator("preferences.rename_addon_search", text="", icon='PREFERENCES')
        op.addon_name = addon_name
        op.prefs_tabs = 'UI'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Draw the UIList without the invalid keyword argument
        layout.template_list("SCENE_UL_CollectionList", "", bpy.data, "collections", scene, "collection_index")

        col = layout.column(align=True)
        row = col.row()
        row.operator("scene.export_selected_collections", text="Export Collections")


# Scene properties to define original_path and replacement_path
def register_scene_properties():
    bpy.types.Scene.collection_index = bpy.props.IntProperty(
        name="Collection Index",
        description="Index of the active collection in the list",
        default=0
    )


    bpy.types.Collection.my_export_select = bpy.props.BoolProperty(
        name="Select for Export",
        description="Select this collection for export",
        default=False
    )

    bpy.types.Scene.export_format = bpy.props.EnumProperty(
        name="Export Format",
        description="Filter collections by export format.",
        items=[
            ('Universal Scene Description', "USD (.usd)", "Export to USD format"),
            ('Alembic', "Alembic (.abc)", "Export to Alembic format"),
            ('Wavefront OBJ', "OBJ (.obj)", "Export to OBJ format"),
            ('Stanford PLY', "PLY (.ply)", "Export to PLY format"),
            ('STL', "STL (.stl)", "Export to STL format"),
            ('FBX', "FBX (.fbx)", "Export to FBX format"),
            ('glTF 2.0', "glTF (.gltf)", "Export to glTF format"),
        ],
        default=bpy.context.preferences.addons[__package__].preferences.default_export_format
    )


def unregister_scene_properties():
    del bpy.types.Scene.original_path
    del bpy.types.Scene.replacement_path
    del bpy.types.Scene.collection_index
    del bpy.types.Scene.use_blender_file_location
    del bpy.types.Scene.custom_export_path
    del bpy.types.Collection.my_export_select


# Register and Unregister classes
classes = (
    SCENE_OT_CreateExportDirectory,
    SCENE_OT_SetExporterPath,
    CustomExporterPreferences,
    SCENE_OT_ExportCollection,
    SCENE_OT_ExportSelectedCollections,
    SCENE_OT_OpenExportDirectory,
    SCENE_UL_CollectionList,
    SCENE_PT_CollectionExportPanel,
    SCENE_OT_SelectAllCollections,
    SCENE_OT_UnselectAllCollections,
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
