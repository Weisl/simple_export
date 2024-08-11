import bpy

from .utils import get_addon_name


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
