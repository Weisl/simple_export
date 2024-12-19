import os

import bpy

from .functions import get_addon_name
from .uilist import color_tag_icons


def get_presets_folder():
    """Retrieve the base path for Blender's presets folder."""
    # Get the user scripts folder dynamically
    return os.path.join(bpy.utils.resource_path('USER'), "scripts", "presets", "operator")


EXPORT_FORMATS = {
    "FBX": {
        "op_name": "IO_FH_fbx",
        "label": "FBX",
        "description": "FBX Export",
        "preset_folder": os.path.join(get_presets_folder(), "export_scene.fbx"),
        "op_type": "<class 'bpy.types.EXPORT_SCENE_OT_fbx'>",
        "file_extension": "fbx",
    },
    "OBJ": {
        "op_name": "IO_FH_obj",
        "label": "OBJ",
        "description": "Wavefront OBJ Export",
        "preset_folder": os.path.join(get_presets_folder(), "wm.obj_export"),
        "op_type": "<class 'bpy.types.WM_OT_obj_export'>",
        "file_extension": "obj",
    },
    "GLTF": {
        "op_name": "IO_FH_gltf2",
        "label": "glTF",
        "description": "glTF 2.0 Export",
        "preset_folder": os.path.join(get_presets_folder(), "export_scene.gltf"),
        "op_type": "<class 'bpy.types.EXPORT_SCENE_OT_gltf'>",
        "file_extension": "glb",
    },
    "USD": {
        "op_name": "IO_FH_usd",
        "label": "USD",
        "description": "Universal Scene Description Export",
        "preset_folder": os.path.join(get_presets_folder(), "wm.usd_export"),
        "op_type": "<class 'bpy.types.WM_OT_usd_export'>",
        "file_extension": "usd",
    },
    "ALEMBIC": {
        "op_name": "IO_FH_alembic",
        "label": "Alembic",
        "description": "Alembic Export",
        "preset_folder": os.path.join(get_presets_folder(), "wm.alembic_export"),
        "op_type": "<class 'bpy.types.WM_OT_alembic_export'>",
        "file_extension": "abc",
    },
    "PLY": {
        "op_name": "IO_FH_ply",
        "label": "PLY",
        "description": "Stanford PLY Export",
        "preset_folder": os.path.join(get_presets_folder(), "wm.ply_export"),
        "op_type": "<class 'bpy.types.WM_OT_ply_export'>",
        "file_extension": "ply",
    },
    "STL": {
        "op_name": "IO_FH_stl",
        "label": "STL",
        "description": "STL Export",
        "preset_folder": os.path.join(get_presets_folder(), "wm.stl_export"),
        "op_type": "<class 'bpy.types.WM_OT_stl_export'>",
        "file_extension": "stl",
    },
}


def draw_export_preset(layout, context):
    scene = context.scene
    props = context.scene.simple_export_props
    prefs = context.preferences.addons[__package__].preferences

    # Select preset
    layout.prop(props, "simple_export_preset_file", text="Preset")


def draw_preset_debug(layout, context):
    scene = context.scene
    props = context.scene.simple_export_props

    box_debug = layout.box()

    box_debug.label(text='Debug')

    row = box_debug.row(align=True)
    row.enabled = False  # Makes the field non-editable
    row.prop(scene, "simple_export_preset_file", text="")
    box_debug.prop(props, "override_path", text="Overwrite Preset Folder")

    row = box_debug.row(align=True)
    row.enabled = props.override_path  # Only enable preset_path editing if override_path is true
    row.prop(props, "preset_path", text="Preset Folder")

    row = box_debug.row()
    op = row.operator("simple_export.assign_preset", text="Assign Preset")
    op.collection_name = context.collection.name


def draw_properties_with_prefix(layout, context, properties):
    """
    Draws properties with a * prefix if they differ between the WindowManager and Preferences.

    Args:
        layout (UILayout): The UI layout to draw in.
        context (Context): The Blender context.
        properties (list): List of property names to compare and draw.
    """
    wm = context.window_manager
    prefs = context.preferences.addons[__package__].preferences

    for prop_name in properties:
        # Ensure the property exists in both WindowManager and Preferences
        if hasattr(wm, prop_name) and hasattr(prefs, prop_name):
            wm_value = getattr(wm, prop_name)
            pref_value = getattr(prefs, prop_name)

            from .preferenecs import PROPERTY_METADATA
            text = PROPERTY_METADATA[prop_name]["name"]

            # Determine label text with prefix
            label_prefix = "* " if wm_value != pref_value else ""
            label_text = f"{label_prefix}{text.replace('_', ' ').title()}"

            # Draw the property with dynamic label
            row = layout.row()
            row.prop(wm, prop_name, text=label_text)
        else:
            # Debugging note: Property does not exist
            print(f"Property {prop_name} not found in WindowManager or Preferences")


def draw_create_export_collection(layout, context):
    wm = context.window_manager

    if not wm.overwrite_collection_settings:
        layout.enabled = False

    # Define properties to check
    properties = [
        "collection_color",
        "use_blend_file_name_as_prefix",
        "custom_prefix",
        "custom_suffix",
        "auto_set_filepath",
        "auto_set_preset",
        "set_location_offset_on_creation"
    ]

    # Use the helper function to draw properties
    draw_properties_with_prefix(layout, context, properties)


def draw_filepath_settings(layout, context):
    wm = context.window_manager

    if not wm.overwrite_filepath_settings:
        layout.enabled = False

    # Define properties to check
    properties_foler = [
        "use_custom_export_folder",
        "custom_export_path",
    ]

    properties = [
        "search_path",
        "replacement_path",
    ]
    # Use the helper function to draw properties
    box = layout.box()
    draw_properties_with_prefix(box, context, properties_foler)
    draw_properties_with_prefix(layout, context, properties)


def draw_custom_collection_ui(self, context):
    """Draw custom UI in the COLLECTION_PT_instancing panel."""
    layout = self.layout
    collection = context.collection

    # Add the Object Picker
    layout.prop(collection, "offset_object", text="Offset Object")


def get_export_format_items():
    return [(key, value["label"], value["description"]) for key, value in EXPORT_FORMATS.items()]


class SimpleExportProperties(bpy.types.PropertyGroup):
    def update_preset_path(self, context):
        self.preset_path = EXPORT_FORMATS[self.export_format]["preset_folder"]

    export_format: bpy.props.EnumProperty(
        name="Export Format",
        description="Select the export format",
        items=get_export_format_items(),  # Dynamically generated items from EXPORT_FORMATS
        default="FBX",
        update=update_preset_path,  # Update the preset path when export format changes
    )

    preset_path: bpy.props.StringProperty(
        name="Preset Folder Path",
        description="Path to the folder containing .py files",
        default=EXPORT_FORMATS["FBX"]["preset_folder"],  # Dynamically fetch from EXPORT_FORMATS
        subtype="DIR_PATH",
    )

    simple_export_preset_file: bpy.props.EnumProperty(
        name="Preset File",
        description="Select a .py file",
        items=lambda self, context: self.get_py_files(),
        update=lambda self, context: self.update_scene_preset_path(context),
    )

    override_path: bpy.props.BoolProperty(
        name="Overwrite Preset Folder",
        description="Manually override the automatically set preset folder",
        default=False,
    )

    def update_scene_preset_path(self, context):
        """Update the full path of the selected preset in the scene property."""
        context.scene.simple_export_preset_file = self.simple_export_preset_file

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
        op = row.operator("simple_export.open_preferences", text="", icon="PREFERENCES")
        op.addon_name = addon_name
        op.prefs_tabs = 'SETTINGS'

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager

        # List Operators
        col = layout.column(align=True)
        row = col.row()
        row.prop(wm, 'move_to_origin')
        row = col.row()
        row.operator("scene.export_selected_collections", text="Export Selected", icon='EXPORT')

        row = col.row()
        row.operator("simple_export.assign_preset_selection", text="Assign Presets", icon='PRESET_NEW')

        row = col.row()
        row.operator("scene.set_export_path_selection", text="Assign Filepaths", icon='FOLDER_REDIRECT')


class SIMPLE_EXPORT_MT_context_menu(bpy.types.Menu):
    bl_label = "Custom Collection Menu"
    bl_idname = "SIMPLE_EXPORT_MT_context_menu"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        op = row.operator("scene.select_all_collections", text="Select All", icon="CHECKBOX_HLT")
        op.invert = False
        row = layout.row()
        op = row.operator("scene.select_all_collections", text="Unselect All", icon="CHECKBOX_DEHLT")
        op.invert = True


class SIMPLE_EXPORT_PT_CollectionExportPanel(SIMPLE_EXPORT_menu_base, bpy.types.Panel):
    bl_idname = "SCENE_PT_simple_export"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"

    def draw(self, context):
        props = context.scene.simple_export_props
        prefs = context.preferences.addons[__package__].preferences

        scene = context.scene
        wm = context.window_manager

        layout = self.layout

        # Draw format selection
        layout.prop(props, "export_format", text="Format")

        # Draw Preset UI
        box = layout.box()
        row = box.row(align=True)
        draw_export_preset(row, context)

        if prefs.simple_export_debug:
            box = box.box()
            draw_preset_debug(box, context)

        # Export List
        row = layout.row()
        row.label(text="Export List")
        row = layout.row()
        row.template_list("SCENE_UL_CollectionList", "scene", bpy.data, "collections", scene, "collection_index")

        # Draw Export List
        super().draw(context)

        # Button to open the export Popup
        op = layout.operator("wm.call_panel", text="Open Export Popup")
        op.name = "SIMPLE_EXPORT_PT_simple_export_popup"

        # Collapsible Filepath Settings Section
        header, body = layout.panel("filepath_settings", default_closed=True)

        # Header
        addon_name = get_addon_name()

        row = header.row(align=True)
        row.prop(wm, 'overwrite_filepath_settings')
        op = row.operator("simple_export.open_preferences", text="", icon="PREFERENCES")
        op.addon_name = addon_name
        op.prefs_tabs = 'SETTINGS'

        # Body
        if body:
            draw_filepath_settings(body, context)

        # Collapsible Export Collection Section
        header, body = layout.panel("export_collection", default_closed=False)

        # Header
        row = header.row(align=True)
        row.prop(wm, 'overwrite_collection_settings')
        op = row.operator("simple_export.open_preferences", text="", icon="PREFERENCES")
        op.addon_name = addon_name
        op.prefs_tabs = 'SETTINGS'

        # Body
        if body:
            draw_create_export_collection(body, context)

        # Parent selection
        row = layout.row()
        color_tag = None
        if context.scene.parent_collection:
            color_tag = context.scene.parent_collection.color_tag
        icon = color_tag_icons.get(color_tag, 'OUTLINER_COLLECTION')
        row.prop(context.scene, "parent_collection", text="Parent Collection", icon=icon)

        # Draw Create Button
        row = layout.row()
        prefs = context.preferences.addons[__package__].preferences
        color_tag = prefs.collection_color
        icon = color_tag_icons.get(color_tag, 'OUTLINER_COLLECTION')
        row.operator("simple_export.create_export_collection", icon=icon)


class SIMPLE_EXPORT_PT_simple_export_popup(SIMPLE_EXPORT_menu_base, bpy.types.Panel):
    bl_idname = "SIMPLE_EXPORT_PT_simple_export_popup"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_context = "empty"
    bl_ui_units_x = 45

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        row = layout.row()
        row.label(text="Simple Export Popup")

        # Export List
        row = layout.row()
        row.label(text="Export List")
        row = layout.row()
        row.template_list("SCENE_UL_CollectionList", "popup", bpy.data, "collections", scene, "collection_index")

        super().draw(context)


classes = (
    SimpleExportProperties,
    SIMPLE_EXPORT_MT_context_menu,
    SIMPLE_EXPORT_PT_CollectionExportPanel,
    SIMPLE_EXPORT_PT_simple_export_popup,
)


# Register and Unregister
def register():
    Scene = bpy.types.Scene
    Scene.simple_export_preset_file = bpy.props.StringProperty(
        name="Simple Export Preset",
        description="Path for Simple Export preset",
        default="",
    )
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    Scene.simple_export_props = bpy.props.PointerProperty(type=SimpleExportProperties)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    Scene = bpy.types.Scene
    del Scene.simple_export_preset_file
    del Scene.simple_export_props
