import bpy
import os

from .. import __package__ as base_package
from ..core.info import ADDON_NAME, COLOR_TAG_ICONS


def get_presets_folder():
    """Retrieve the base path for Blender's presets folder."""
    # Get the user scripts folder dynamically
    return os.path.join(bpy.utils.resource_path('USER'), "scripts", "presets", "operator")


def draw_preset_settings(layout, context):
    """
    Draw the preset property dynamically based on the selected export format.
    """
    scene = context.scene
    prefs = context.preferences.addons[base_package].preferences
    export_format = scene.export_format  # Get the currently selected export format

    # Dynamically determine the property name
    prop_name = f"simple_export_preset_file_{export_format.lower()}"

    if scene.overwrite_preset_settings:
        set = scene
        label = 'Preset'

    else:  # scene.overwrite_preset_settings:
        layout.enabled = False
        set = prefs
        label = 'Default Preset'

    if hasattr(set, prop_name):
        layout.prop(set, prop_name, text=label)
    else:
        layout.label(text=f"No presets available for {export_format}", icon="ERROR")


def draw_properties_with_prefix(layout, context, properties):
    """
    Draws properties with a * prefix if they differ between the Scene and Preferences.

    Args:
        layout (UILayout): The UI layout to draw in.
        context (Context): The Blender context.
        properties (list): List of property names to compare and draw.
    """
    scene = context.scene
    prefs = context.preferences.addons[base_package].preferences

    for prop_name in properties:
        # Ensure the property exists in both Scene and Preferences
        if hasattr(scene, prop_name) and hasattr(prefs, prop_name):
            scene_value = getattr(scene, prop_name)
            pref_value = getattr(prefs, prop_name)

            from ..preferences.preferenecs import PROPERTY_METADATA
            text = PROPERTY_METADATA[prop_name]["name"]

            # Determine label text with prefix
            label_prefix = "* " if scene_value != pref_value else ""
            label_text = f"{label_prefix}{text.replace('_', ' ').title()}"

            # Draw the property with dynamic label
            row = layout.row()
            row.prop(scene, prop_name, text=label_text)
        else:
            # Debugging note: Property does not exist
            print(f"Property {prop_name} not found in Scene or Preferences")


def draw_create_export_collections(layout, context):
    scene = context.scene

    if not scene.overwrite_collection_settings:
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
    scene = context.scene

    if not scene.overwrite_filepath_settings:
        layout.enabled = False

    # Define properties to check
    properties_foler = [
        "custom_export_path",
    ]

    properties = [
        "search_path",
        "replacement_path",
    ]

    # Use the helper function to draw properties
    layout.prop(scene, "use_custom_export_folder")
    if scene.use_custom_export_folder:
        draw_properties_with_prefix(layout, context, properties_foler)
    if not scene.use_custom_export_folder:
        draw_properties_with_prefix(layout, context, properties)


def draw_custom_collection_ui(self, context):
    """Draw custom UI in the COLLECTION_PT_instancing panel."""
    layout = self.layout
    collection = context.collection

    # Add the Object Picker
    layout.prop(collection, "offset_object", text="Offset Object")


class SIMPLE_EXPORT_menu_base:
    bl_label = "Simple Export"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row(align=True)

        # Open documentation
        row.operator("wm.url_open", text="", icon="HELP").url = "https://weisl.github.io/exporter_overview/"

        # Open Preferences
        addon_name = ADDON_NAME
        op = row.operator("simple_export.open_preferences", text="", icon="PREFERENCES")
        op.addon_name = addon_name
        op.prefs_tabs = 'SETTINGS'

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # List Operators
        box = layout.box()
        col = box.column(align=True)
        row = col.row()

        icon = 'WARNING_LARGE' if bpy.app.version >= (4, 3, 0) else 'ERROR'
        row.label(text="Pre Export Operations (BETA)", icon=icon)
        row = col.row()
        row.prop(scene, 'move_by_collection_offset')

        col = layout.column(align=True)
        row = col.row()
        op = row.operator("simple_export.assign_preset_selection", text="Assign Presets", icon='PRESET_NEW')
        op.outliner = False

        row = col.row()
        op = row.operator("scene.set_export_path_selection", text="Assign Filepaths", icon='FOLDER_REDIRECT')
        op.outliner = False

        col.separator()
        row = col.row()
        op = row.operator("simple_export.export_selected_collections", text="Export Selected", icon='EXPORT')
        op.outliner = False
        op.individual_collection = False


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
        prefs = context.preferences.addons[base_package].preferences

        scene = context.scene

        layout = self.layout

        # Draw format selection
        layout.prop(scene, "export_format", text="Format")

        # Export List
        row = layout.row()
        row.label(text="Export List")

        row = layout.row(align=True)
        op = row.operator("scene.select_all_collections", text="All", icon="CHECKBOX_HLT")
        op.invert = False
        op = row.operator("scene.select_all_collections", text="None", icon="CHECKBOX_DEHLT")
        op.invert = True

        layout.template_list("SCENE_UL_CollectionList", "scene", bpy.data, "collections", scene, "collection_index")

        # Draw Export List
        super().draw(context)

        # Button to open the export Popup
        op = layout.operator("wm.call_panel", text="Open Export Popup")
        op.name = "SIMPLE_EXPORT_PT_simple_export_popup"

        # Collapsible Filepath Settings Section
        header, body = layout.panel("overwrite_settings", default_closed=False)

        # Header
        addon_name = ADDON_NAME

        row = header.row(align=True)
        row.label(text='Overwrite Preferences')
        op = row.operator("simple_export.open_preferences", text="", icon="PREFERENCES")
        op.addon_name = addon_name
        op.prefs_tabs = 'SETTINGS'

        # Body
        if body:
            row = body.row()
            row.prop(scene, 'overwrite_filepath_settings')
            box = body.box()
            draw_filepath_settings(box, context)

            row = body.row()
            row.prop(scene, 'overwrite_preset_settings')
            box = body.box()
            draw_preset_settings(box, context)

            row = body.row()
            row.prop(scene, 'overwrite_collection_settings')

            box = body.box()
            draw_create_export_collections(box, context)

        # Parent selection
        row = layout.row()
        color_tag = None
        if context.scene.parent_collection:
            color_tag = context.scene.parent_collection.color_tag
        icon = COLOR_TAG_ICONS.get(color_tag, 'OUTLINER_COLLECTION')
        row.prop(context.scene, "parent_collection", text="Parent Collection", icon=icon)

        # Draw Create Button
        row = layout.row()
        prefs = context.preferences.addons[base_package].preferences
        color_tag = prefs.collection_color
        icon = COLOR_TAG_ICONS.get(color_tag, 'OUTLINER_COLLECTION')
        row.operator("simple_export.create_export_collections", icon=icon)

        # row = layout.row()
        # row.operator("simple_export.add_settings_to_collections")


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

        row = layout.row(align=True)
        op = row.operator("scene.select_all_collections", text="All", icon="CHECKBOX_HLT")
        op.invert = False
        op = row.operator("scene.select_all_collections", text="None", icon="CHECKBOX_DEHLT")
        op.invert = True

        row = layout.row()
        row.template_list("SCENE_UL_CollectionList", "popup", bpy.data, "collections", scene, "collection_index")

        super().draw(context)


classes = (
    SIMPLE_EXPORT_MT_context_menu,
    SIMPLE_EXPORT_PT_CollectionExportPanel,
    SIMPLE_EXPORT_PT_simple_export_popup,
)


# Register and Unregister
def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
