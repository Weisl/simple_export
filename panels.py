import bpy
from bpy.types import Menu

from .functions import get_addon_name
from .presets.naming_preset import get_preset_folder_path


def draw_naming_presets(self, context):
    """
    Draw the naming presets menu in the layout.

    Args:
        self (UILayout): The UI layout.
        context (Context): The current context.
    """
    layout = self.layout
    row = layout.row(align=True)

    row.menu(EXPORT_MT_collision_presets.__name__, text=EXPORT_MT_collision_presets.bl_label)
    addon_name = get_addon_name()

    op = row.operator("explorer.open_in_explorer", text="", icon='FILE_FOLDER')
    op.dirpath = get_preset_folder_path()

    op = row.operator("preferences.addon_search", text="", icon='PREFERENCES')
    op.addon_name = addon_name
    op.prefs_tabs = 'NAMING'


def draw_custom_collection_ui(self, context):
    """Draw custom UI in the COLLECTION_PT_instancing panel."""
    layout = self.layout
    collection = context.collection

    # Add the Object Picker
    layout.prop(collection, "offset_object", text="Offset Object")


############## PRESET ##############################

class EXPORT_MT_collision_presets(Menu):
    """Collider preset dropdown"""

    bl_label = "Export Presets"
    bl_description = "Specify export preset"
    preset_subdir = "simple_export"
    preset_operator = "collision.load_collision_preset"
    subclass = 'PresetMenu'
    draw = Menu.draw_preset


class SIMPLE_EXPORTER_menu_base:
    bl_label = "Simple Export"

    def draw_header(self, context):
        layout = self.layout
        row = layout.row(align=True)

        # Open documentation
        row.operator("wm.url_open", text="", icon='HELP').url = "https://weisl.github.io/exporter_overview/"

        # Open Preferences
        addon_name = get_addon_name()
        op = row.operator("preferences.rename_addon_search", text="", icon='PREFERENCES')
        op.addon_name = addon_name

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        row = layout.row()
        # Draw the UIList without the invalid keyword argument
        row.template_list("SCENE_UL_CollectionList", '', bpy.data, "collections", scene, "collection_index")
        col = row.column(align=True)
        col.menu("SIMPLE_EXPORTER_MT_context_menu", icon='DOWNARROW_HLT', text="")

        col = layout.column(align=True)
        row = col.row()
        row.operator("scene.export_selected_collections", text="Export Collections")


class SIMPLE_EXPORTER_MT_context_menu(bpy.types.Menu):
    bl_label = "Custom Collection Menu"
    bl_idname = "SIMPLE_EXPORTER_MT_context_menu"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.operator("scene.select_all_collections", text="Select All", icon='CHECKBOX_HLT')
        row = layout.row()
        row.operator("scene.unselect_all_collections", text="Unselect All", icon='CHECKBOX_DEHLT')


class SIMPLE_EXPORTER_PT_CollectionExportPanel(SIMPLE_EXPORTER_menu_base, bpy.types.Panel):
    bl_idname = "SCENE_PT_simple_export"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"

    def draw(self, context):
        super().draw(context)
        layout = self.layout

        # Add a button to open the panel as a popup
        op = layout.operator("wm.call_panel", text="Open Export Popup")
        op.name = "SIMPLE_EXPORTER_PT_simple_export"

        draw_naming_presets(self, context)


class SIMPLE_EXPORTER_PT_simple_export(SIMPLE_EXPORTER_menu_base, bpy.types.Panel):
    bl_idname = "SIMPLE_EXPORTER_PT_simple_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'WINDOW'
    bl_context = "empty"
    bl_ui_units_x = 45

    def draw(self, context):
        layout = self.layout

        row = layout.row()
        row.label(text="Simple Export Popup")

        super().draw(context)


classes = (EXPORT_MT_collision_presets,
           SIMPLE_EXPORTER_MT_context_menu,
           SIMPLE_EXPORTER_PT_CollectionExportPanel,
           SIMPLE_EXPORTER_PT_simple_export)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
