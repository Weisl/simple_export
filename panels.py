import bpy

from .utils import get_addon_name


class SCENE_PT_CollectionExportPanel(bpy.types.Panel):
    bl_label = "Simple Export"
    bl_idname = "SCENE_PT_simple_export"
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

def draw_custom_collection_ui(self, context):
    """Draw custom UI in the COLLECTION_PT_instancing panel."""
    layout = self.layout
    collection = context.collection

    # Add the Object Picker
    layout.prop(collection, "offset_object", text="Offset Object")

    # Add an operator button to manually update the offset if needed
    layout.operator("object.set_collection_offset", text="Set Collection Offset")


