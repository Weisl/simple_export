import os

import bpy

from .functions import get_addon_name


def get_presets_folder():
    """Retrieve the base path for Blender's presets folder."""
    # Get the user scripts folder dynamically
    return os.path.join(bpy.utils.resource_path('USER'), "scripts", "presets", "operator")


EXPORT_PRESET_FOLDERS = {
    "FBX": os.path.join(get_presets_folder(), "export_scene.fbx"),
    "OBJ": os.path.join(get_presets_folder(), "wm.obj_export"),
    "GLTF": os.path.join(get_presets_folder(), "export_scene.gltf"),
    "USD": os.path.join(get_presets_folder(), "wm.usd_export"),
    "ALEMBIC": os.path.join(get_presets_folder(), "wm.alembic_export"),
}


def draw_export_preset(self, context):
    layout = self.layout
    scene = context.scene
    props = context.scene.simple_export_props

    layout.prop(props, "export_format", text="Export Format")

    box = layout.box()
    box.label(text="Presets")
    box.prop(props, "override_path", text="Override Preset Folder")

    row = box.row(align=True)
    row.enabled = props.override_path  # Only enable preset_path editing if override_path is true
    row.prop(props, "preset_path", text="Preset Folder")

    box.prop(props, "simple_export_preset_path", text="Preset File")

    row = box.row(align=True)
    row.label(text="Active Preset")
    row = box.row(align=True)
    row.enabled = False  # Makes the field non-editable
    row.prop(scene, "simple_export_preset_path", text="")

    row = layout.row(align=True)
    row.operator("simple_export.apply_preset", text="Apply Preset")


def draw_custom_collection_ui(self, context):
    """Draw custom UI in the COLLECTION_PT_instancing panel."""
    layout = self.layout
    collection = context.collection

    # Add the Object Picker
    layout.prop(collection, "offset_object", text="Offset Object")


class SimpleExporterProperties(bpy.types.PropertyGroup):
    export_format: bpy.props.EnumProperty(
        name="Export Format",
        description="Select the export format",
        items=[
            ("FBX", "FBX", "FBX Export"),
            ("OBJ", "OBJ", "OBJ Export"),
            ("GLTF", "glTF", "glTF Export"),
            ("USD", "USD", "USD Export"),
            ("ALEMBIC", "Alembic", "Alembic Export"),
        ],
        default="FBX",
        update=lambda self, context: self.update_preset_path(),
    )
    preset_path: bpy.props.StringProperty(
        name="Preset Folder Path",
        description="Path to the folder containing .py files",
        default=EXPORT_PRESET_FOLDERS["FBX"],  # Use the folder for the default format
        subtype="DIR_PATH",
    )
    simple_export_preset_path: bpy.props.EnumProperty(
        name="Preset File",
        description="Select a .py file",
        items=lambda self, context: self.get_py_files(),
        update=lambda self, context: self.update_scene_preset_path(context),
    )
    override_path: bpy.props.BoolProperty(
        name="Override Preset Folder",
        description="Manually override the automatically set preset folder",
        default=False,
    )


    def update_preset_path(self):
        """Automatically set the preset path based on the export format unless overridden."""
        if not self.override_path:
            self.preset_path = EXPORT_PRESET_FOLDERS.get(self.export_format, "")

    def update_scene_preset_path(self, context):
        """Update the full path of the selected preset in the scene property."""
        context.scene.simple_export_preset_path = self.simple_export_preset_path

    def get_py_files(self):
        """Retrieve all .py files from the specified folder."""
        if not self.preset_path:
            return [("", "No Path", "No path specified")]

        try:
            files = [
                (os.path.join(self.preset_path, f), f, "")
                for f in os.listdir(self.preset_path)
                if f.endswith(".py")
            ]
            return files if files else [("", "No Files", "No .py files found")]
        except Exception as e:
            return [("", "Error", str(e))]


class SIMPLE_EXPORT_menu_base:
    bl_label = "Simple Export"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row(align=True)

        # Open documentation
        row.operator("wm.url_open", text="", icon="HELP").url = "https://weisl.github.io/exporter_overview/"

        # Open Preferences
        addon_name = get_addon_name()
        op = row.operator("preferences.rename_addon_search", text="", icon="PREFERENCES")
        op.addon_name = addon_name

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        draw_export_preset(self, context)

        row = layout.row()
        row.label(text="Export List")
        row = layout.row()
        row.template_list("SCENE_UL_CollectionList", "", bpy.data, "collections", scene, "collection_index")
        col = row.column(align=True)
        col.menu("SIMPLE_EXPORT_MT_context_menu", icon="DOWNARROW_HLT", text="")

        col = layout.column(align=True)
        row = col.row()
        row.operator("scene.export_selected_collections", text="Export Collections")


class SIMPLE_EXPORT_MT_context_menu(bpy.types.Menu):
    bl_label = "Custom Collection Menu"
    bl_idname = "SIMPLE_EXPORT_MT_context_menu"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.operator("scene.select_all_collections", text="Select All", icon="CHECKBOX_HLT")
        row = layout.row()
        row.operator("scene.unselect_all_collections", text="Unselect All", icon="CHECKBOX_DEHLT")


class SIMPLE_EXPORT_PT_CollectionExportPanel(SIMPLE_EXPORT_menu_base, bpy.types.Panel):
    bl_idname = "SCENE_PT_simple_export"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        super().draw(context)
        layout = self.layout

        # Add a button to open the panel as a popup
        op = layout.operator("wm.call_panel", text="Open Export Popup")
        op.name = "SIMPLE_EXPORT_PT_simple_export"


class SIMPLE_EXPORT_PT_simple_export(SIMPLE_EXPORT_menu_base, bpy.types.Panel):
    bl_idname = "SIMPLE_EXPORT_PT_simple_export"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_context = "empty"
    bl_ui_units_x = 45

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text="Simple Export Popup")

        super().draw(context)


classes = (
    SimpleExporterProperties,
    SIMPLE_EXPORT_MT_context_menu,
    SIMPLE_EXPORT_PT_CollectionExportPanel,
    SIMPLE_EXPORT_PT_simple_export,
)


def register():
    Scene = bpy.types.Scene
    Scene.simple_export_preset_path = bpy.props.StringProperty(
        name="Simple Exporter Preset",
        description="Path for Simple Exporter preset",
        default="",
    )

    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    Scene.simple_export_props = bpy.props.PointerProperty(type=SimpleExporterProperties)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    Scene = bpy.types.Scene
    del Scene.simple_export_preset_path
    del Scene.simple_export_props
