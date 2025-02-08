import bpy

from .properties_panels import SIMPLE_EXPORT_menu_base
from .. import __package__ as base_package
from ..core.info import ADDON_NAME
from ..ui.properties_panels import COLOR_TAG_ICONS, draw_filepath_settings, draw_preset_settings, \
    draw_create_export_collections


class VIEW3D_PT_SimpleExport(SIMPLE_EXPORT_menu_base, bpy.types.Panel):
    """Creates a Panel in the Object properties window"""

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Simple Export"
    bl_label = ""

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
        row.label(text="Simple Export")
        # Open Export Popup
        op = row.operator("wm.call_panel", text="", icon="WINDOW")
        op.name = "SIMPLE_EXPORT_PT_simple_export_popup"

    def draw(self, context):
        prefs = context.preferences.addons[base_package].preferences

        scene = context.scene

        layout = self.layout
        layout.label(text="Batch Export Collections")

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

        # Display export list
        layout.template_list("SCENE_UL_CollectionList", "npanel", bpy.data, "collections", scene, "collection_index")

        # Ensure a valid selection before displaying details
        if 0 <= scene.collection_index < len(bpy.data.collections):
            selected_collection = bpy.data.collections[scene.collection_index]

            # First Compact UI List - Collection Name & Icon
            layout.template_list(
                "SCENE_UL_CollectionDetails",
                "details_general",  # Unique ID for general info
                bpy.data,
                "collections",
                scene,
                "collection_index",
                type='COMPACT'
            )

            # Second Compact UI List - Export Path & Additional Settings
            layout.template_list(
                "SCENE_UL_CollectionDetails",
                "details_export",  # Unique ID for export properties
                bpy.data,
                "collections",
                scene,
                "collection_index",
                type='COMPACT'
            )

        layout.separator()

        # Draw Export List
        super().draw(context)

        # Collapsible Filepath Settings Section
        header, body = layout.panel("overwrite_settings", default_closed=False)

        # Header
        addon_name = ADDON_NAME

        row = header.row(align=True)
        row.label(text='Scene Settings')
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


classes = (
    VIEW3D_PT_SimpleExport,
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
