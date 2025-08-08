import os

import bpy

from .. import __package__ as base_package
from ..core.info import ADDON_NAME, COLOR_TAG_ICONS
from ..functions.exporter_funcs import find_exporter


def draw_pre_export_operations(col, scene):
    # Ensure the panel is collapsed by default
    header, body = col.panel(idname="PRE_EXPORT_OPERATIONS_PANEL", default_closed=True)

    icon = 'WARNING_LARGE' if bpy.app.version >= (4, 3, 0) else 'ERROR'

    # Draw the panel header
    header.label(text="Pre Export Operations (BETA)", icon=icon)

    # Check if the panel is expanded before drawing elements
    if body:
        body.prop(scene, 'move_by_collection_offset')


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
        prefs = context.preferences.addons[base_package].preferences

        # Draw File Format Selection
        row = body.row()
        row.prop(scene, "export_format", text="Format")

        # Filepath Settings
        row = body.row()
        row.prop(scene, 'overwrite_filepath_settings')
        box = body.box()
        filepath_settings = scene if scene.overwrite_filepath_settings else prefs
        if scene.overwrite_filepath_settings:
            box.enabled = True
        else:
            box.enabled = False

        # Draw filepath properties using shared function
        from ..ui.shared_draw import draw_export_folderpath_properties
        draw_export_folderpath_properties(box, filepath_settings)

        # Filename Settings
        row = body.row()
        row.prop(scene, 'overwrite_filename_settings')
        box = body.box()
        filename_settings = scene if scene.overwrite_filename_settings else prefs
        if scene.overwrite_filename_settings:
            box.enabled = True
        else:
            box.enabled = False

        # Draw filename properties using shared function
        from ..ui.shared_draw import draw_export_filename_properties
        draw_export_filename_properties(box, filename_settings)

        # Preset Settings
        row = body.row()
        row.prop(scene, 'overwrite_preset_settings')
        box = body.box()
        preset_settings = scene if scene.overwrite_preset_settings else prefs
        if scene.overwrite_preset_settings:
            box.enabled = True
        else:
            box.enabled = False

        # Draw preset properties using shared function
        from ..ui.shared_draw import draw_export_preset_properties
        draw_export_preset_properties(box, preset_settings)

        # Collection Settings
        row = body.row()
        row.prop(scene, 'overwrite_collection_settings')
        box = body.box()
        collection_settings = scene if scene.overwrite_collection_settings else prefs
        if scene.overwrite_collection_settings:
            box.enabled = True
        else:
            box.enabled = False

        # Draw collection name properties using shared function
        from ..ui.shared_draw import draw_collection_name_properties
        draw_collection_name_properties(box, collection_settings)

        # Draw collection settings properties using shared function
        from ..ui.shared_draw import draw_collection_settings_properties
        draw_collection_settings_properties(box, collection_settings)


def draw_active_list_element(layout, context, scene):
    # Ensure valid selection before showing details
    if 0 <= scene.collection_index < len(bpy.data.collections):
        selected_collection = bpy.data.collections[scene.collection_index]

        # Draw the panel header
        header, body = layout.panel(idname="ACTIVE_COL_PANEL", default_closed=True)
        header.label(text=f"Active Collection:", icon='OUTLINER_COLLECTION')

        if body:
            # Export Path
            exporter = find_exporter(selected_collection, scene.export_format)

            # Return early
            if not exporter:
                layout.label(text='Select Collection', icon='INFO')
                return

            box = layout.box()
            # Collection name and icon
            row = box.row(align=True)

            row.prop(selected_collection, 'name', icon='OUTLINER_COLLECTION')
            op = row.operator("simple_export.open_exporter_in_properties", text="",
                              icon='PROPERTIES')
            op.collection_name = selected_collection.name

            row = box.row(align=True)
            row.prop(exporter.export_properties, "filepath", text="", expand=True)

            from .shared_operator_call import call_simple_export_path_ops
            op = call_simple_export_path_ops(context, row, selected_collection, text='', outliner=False,
                                             individual_collection=True, collection_name=selected_collection.name)

            row = box.row(align=True)
            row.label(text='Root Object')

            row = box.row(align=True)

            box.prop(selected_collection, "use_root_object", text="Use Root Object")

            # No valid root object
            if not selected_collection.use_root_object:
                root_box = box.box()
                row = root_box.row(align=True)
                # Draw existing instancing properties
                row.prop(selected_collection, "instance_offset", text='Collection Center')

                col = root_box.column(align=True)
                # Add an operator button to manually update the offset if needed
                op = col.operator("object.set_collection_offset_cursor", text="Set Offset from Cursor")
                op.collection_name = selected_collection.name
                op = col.operator("object.set_collection_offset_object", text="Set Offset from Object")
                op.collection_name = selected_collection.name

            # Add the Object Picker
            else:
                box.prop(selected_collection, "root_object", text="Root Object")
                root_box = box.box()

                if selected_collection["root_object"]:
                    root_box.enabled = False
                    row = root_box.row(align=True)
                    # Draw existing instancing properties
                    row.prop(selected_collection, "instance_offset", text='Collection Center')
                else:
                    row = root_box.row(align=True)
                    # Draw existing instancing properties
                    row.prop(selected_collection, "instance_offset", text='Collection Center')

                    col = root_box.column(align=True)
                    # Add an operator button to manually update the offset if needed
                    op = col.operator("object.set_collection_offset_cursor", text="Set Offset from Cursor")
                    op.collection_name = selected_collection.name
                    op = col.operator("object.set_collection_offset_object", text="Set Offset from Object")
                    op.collection_name = selected_collection.name


def draw_export_list(layout, list_id, scene):
    # Export List
    row = layout.row()
    row.label(text="Export List")
    row = layout.row(align=True)
    op = row.operator("scene.select_all_collections", text="All", icon="CHECKBOX_HLT")
    op.deselect = False
    op = row.operator("scene.select_all_collections", text="None", icon="CHECKBOX_DEHLT")
    op.deselect = True
    # Display export list
    layout.template_list("SCENE_UL_CollectionList", list_id, bpy.data, "collections", scene, "collection_index")


def get_presets_folder():
    """Retrieve the base path for Blender's presets_export folder."""
    # Get the user scripts folder dynamically
    return os.path.join(bpy.utils.resource_path('USER'), "scripts", "presets_export", "operator")


def draw_properties_with_prefix(setting, layout, context, properties):
    """
    Draws properties with a * prefix if they differ between the Scene and Preferences.

    Args:
        layout (UILayout): The UI layout to draw in.
        context (Context): The Blender context.
        properties (list): List of property names to compare and draw.
    """

    prefs = context.preferences.addons[base_package].preferences

    for prop_name in properties:
        # Ensure the property exists in both Scene and Preferences
        if hasattr(setting, prop_name) and hasattr(prefs, prop_name):
            scene_value = getattr(setting, prop_name)
            pref_value = getattr(setting, prop_name)

            from ..preferences.preferenecs import PROPERTY_METADATA
            text = PROPERTY_METADATA[prop_name]["name"]

            # Determine label text with prefix
            label_prefix = "* " if scene_value != pref_value else ""
            label_text = f"{label_prefix}{text.replace('_', ' ').title()}"

            # Draw the property with dynamic label
            row = layout.row()
            row.prop(setting, prop_name, text=label_text)
        else:
            # Debugging note: Property does not exist
            print(f"Property {prop_name} not found in Scene or Preferences")


def draw_custom_collection_ui(self, context):
    """Draw custom UI in the COLLECTION_PT_instancing panel."""
    layout = self.layout
    collection = context.collection

    # Add the Object Picker
    layout.prop(collection, "root_object", text="Offset Object")


class SIMPLE_EXPORT_menu_base:
    bl_label = ""

    def draw_header(self, context):
        layout = self.layout
        draw_simple_export_header(layout)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)
        row = col.row()

        from .shared_operator_call import call_set_preset_op
        call_set_preset_op(context, row)

        from .shared_operator_call import call_simple_export_path_ops
        row = col.row()
        op = call_simple_export_path_ops(context, row, outliner=False, individual_collection=False)

        col.separator()
        box = col.box()
        draw_pre_export_operations(box, scene)

        row = col.row()
        op = row.operator("simple_export.export_collections", text="Export Selected", icon='EXPORT')
        op.outliner = False
        op.individual_collection = False


class VIEW3D_PT_SimpleExport(SIMPLE_EXPORT_menu_base, bpy.types.Panel):
    """Creates a Panel in the Object properties window"""

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Simple Export"
    bl_label = ""

    def draw_header(self, context):
        layout = self.layout
        draw_simple_export_header(layout)

    def draw(self, context):
        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene

        layout = self.layout

        list_id = "npanel"

        from .shared_draw import draw_exporter_presets
        draw_exporter_presets(self, context)

        # draw Create exporter
        from .shared_draw import draw_parent_collection, draw_collection_creation
        row = layout.row()
        draw_parent_collection(context, row)
        row = layout.row()
        draw_collection_creation(context, row)

        # draw Export List
        draw_export_list(layout, list_id, scene)

        # Draw Operator List
        super().draw(context)

        draw_active_list_element(layout, context, scene)

        draw_scene_settings_overwrite(context, layout, scene)


class SIMPLE_EXPORT_MT_context_menu(bpy.types.Menu):
    bl_label = "Custom Collection Menu"
    bl_idname = "SIMPLE_EXPORT_MT_context_menu"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        op = row.operator("scene.select_all_collections", text="Select All", icon="CHECKBOX_HLT")
        op.deselect = False
        row = layout.row()
        op = row.operator("scene.select_all_collections", text="Unselect All", icon="CHECKBOX_DEHLT")
        op.deselect = True


class SIMPLE_EXPORT_PT_CollectionExportPanel(SIMPLE_EXPORT_menu_base, bpy.types.Panel):
    bl_idname = "SCENE_PT_simple_export"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"

    def draw(self, context):
        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene

        layout = self.layout

        list_id = "scene"

        from .shared_draw import draw_exporter_presets
        draw_exporter_presets(self, context)

        # draw Create exporter
        from .shared_draw import draw_parent_collection, draw_collection_creation
        row = layout.row()
        draw_parent_collection(context, row)
        row = layout.row()
        draw_collection_creation(context, row)

        draw_export_list(layout, list_id, scene)

        # Draw Operator List
        super().draw(context)

        draw_active_list_element(layout, context, scene)

        draw_scene_settings_overwrite(context, layout, scene)


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

        row = layout.row()
        # draw Create exporter
        from .shared_draw import draw_parent_collection, draw_collection_creation
        draw_parent_collection(context, row)
        draw_collection_creation(context, row)

        # Export List
        row = layout.row()

        row = layout.row(align=True)
        op = row.operator("scene.select_all_collections", text="All", icon="CHECKBOX_HLT")
        op.deselect = False
        op = row.operator("scene.select_all_collections", text="None", icon="CHECKBOX_DEHLT")
        op.deselect = True

        row = layout.row()
        row.template_list("SCENE_UL_CollectionList", "popup", bpy.data, "collections", scene, "collection_index")

        super().draw(context)


classes = (
    VIEW3D_PT_SimpleExport,
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
