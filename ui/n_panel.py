import bpy

from .. import __package__ as base_package
from ..core.info import ADDON_NAME
from ..ui.properties_panels import COLOR_TAG_ICONS, draw_filepath_settings, draw_preset_settings, \
    draw_create_export_collections


class VIEW3D_PT_SimpleExport(bpy.types.Panel):
    """Creates a Panel in the Object properties window"""

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Simple Export"
    bl_label = "Simple Export"

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
