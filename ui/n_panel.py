import bpy

from .properties_panels import SIMPLE_EXPORT_menu_base
from .. import __package__ as base_package
from ..core.info import ADDON_NAME
from ..functions.exporter_funcs import find_exporter
from ..ui.properties_panels import COLOR_TAG_ICONS, draw_filepath_settings, draw_preset_settings, \
    draw_create_export_collections


def draw_simple_export_header(layout):
    row = layout.row(align=True)
    # Open documentation
    row.operator("wm.url_open", text="", icon="HELP").url = "https://weisl.github.io/exporter_overview/"
    # Open Preferences
    addon_name = ADDON_NAME
    op = row.operator("simple_export.open_preferences", text="", icon="PREFERENCES")
    op.addon_name = addon_name
    op.prefs_tabs = 'SETTINGS'
    # Open Export Popup
    op = row.operator("wm.call_panel", text="", icon="WINDOW")
    op.name = "SIMPLE_EXPORT_PT_simple_export_popup"
    row.label(text="Simple Export")


def draw_collection_creation(context, layout):
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


def draw_scene_settings_overwrite(context, layout, scene):
    # Collapsible Filepath Settings Section
    header, body = layout.panel("overwrite_settings", default_closed=False)
    # Header
    addon_name = ADDON_NAME
    row = header.row(align=True)
    row.label(text='Exporter Settings (Scene)')
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


def draw_active_list_element(layout, scene):
    # Ensure valid selection before showing details
    if 0 <= scene.collection_index < len(bpy.data.collections):
        selected_collection = bpy.data.collections[scene.collection_index]

        # Draw the panel header
        header, body = layout.panel(idname="ACTIVE_COL_PANEL", default_closed=True)
        header.label(text=f"Active Collection:", icon='OUTLINER_COLLECTION')

        # Check if the panel is expanded before adding UI elements
        if body:
            box = layout.box()
            # Collection name and icon
            row = box.row(align=True)
            row.prop(selected_collection, 'name', icon='OUTLINER_COLLECTION')
            op = row.operator("simple_export.go_to_collection_exporter", text="",
                              icon='PROPERTIES')
            op.collection_name = selected_collection.name

            # Export Path
            exporter = find_exporter(selected_collection, scene.export_format)
            if exporter:
                row = box.row(align=True)
                row.prop(exporter.export_properties, "filepath", text="", expand=True)
                op = row.operator("simple_export.set_export_paths", text="", icon='FOLDER_REDIRECT')
                op.outliner = False
                op.individual_collection = True
                op.collection_name = selected_collection.name

            # Collection Offset
            row = box.row(align=True)
            row.label(text='Collection Offset (BETA)')
            row = box.row(align=True)
            row.prop(selected_collection, "instance_offset", text='Offset')
            row.menu("COLLECTION_MT_context_menu_instance_offset", icon='DOWNARROW_HLT', text="")


def draw_export_list(layout, list_id, scene):
    # Export List
    row = layout.row()
    row.label(text="Export List")
    row = layout.row(align=True)
    op = row.operator("scene.select_all_collections", text="All", icon="CHECKBOX_HLT")
    op.invert = False
    op = row.operator("scene.select_all_collections", text="None", icon="CHECKBOX_DEHLT")
    op.invert = True
    # Display export list
    layout.template_list("SCENE_UL_CollectionList", list_id, bpy.data, "collections", scene, "collection_index")


class VIEW3D_PT_SimpleExport(SIMPLE_EXPORT_menu_base, bpy.types.Panel):
    """Creates a Panel in the Object properties window"""

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Simple Export"
    bl_label = ""

    def draw_header(self, context):
        layout = self.layout
        from .properties_panels import draw_simple_export_header
        draw_simple_export_header(layout)

    def draw(self, context):
        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene

        layout = self.layout
        layout.label(text="Batch Export Collections")

        # Draw format selection
        layout.prop(scene, "export_format", text="Format")

        list_id = "npanel"

        draw_export_list(layout, list_id, scene)

        # Draw Operator List
        super().draw(context)

        draw_active_list_element(layout, scene)

        draw_scene_settings_overwrite(context, layout, scene)
        draw_collection_creation(context, layout)


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
