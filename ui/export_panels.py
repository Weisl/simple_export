import os

import bpy

from .. import __package__ as base_package
from ..core.export_formats import get_export_format_items
from ..core.info import ADDON_NAME
from ..functions.exporter_funcs import find_exporter


def draw_pre_export_operations(layout, scene):
    # Ensure the panel is collapsed by default
    # header, body = col.panel(idname="PRE_EXPORT_OPERATIONS_PANEL", default_closed=False)

    # Use a warning icon for Blender 4.3 and above, else use error icon
    icon = 'WARNING_LARGE' if bpy.app.version >= (4, 3, 0) else 'ERROR'

    # Draw the panel header
    layout.label(text="Pre Export Operations", icon=icon)

    # Check if the panel is expanded before drawing elements
    # if body:
    layout.prop(scene, 'move_by_collection_offset')


def draw_simple_export_header(layout, text="Simple Export"):
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
    row.label(text=text)


def draw_scene_settings_overwrite(context, layout, scene):
    # Collapsible Filepath Settings Section

    from .shared_draw import draw_exporter_presets
    draw_exporter_presets(layout, buttons=True)

    from .shared_draw import draw_full_exporer_settings
    draw_full_exporer_settings(layout, scene)


def draw_active_list_element(layout, context, scene):
    # Ensure valid selection before showing details
    if 0 <= scene.collection_index < len(bpy.data.collections):
        selected_collection = bpy.data.collections[scene.collection_index]

        # Draw the panel header
        header, body = layout.panel(idname="ACTIVE_COL_PANEL", default_closed=True)
        header.label(text=f"Active Collection:", icon='OUTLINER_COLLECTION')

        if body:
            # Export Path
            exporter = find_exporter(selected_collection, format_filter=scene.export_format)

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


def get_preset_format_folder():
    """Retrieve the base path for Blender's presets export folder."""
    # Get the user scripts folder dynamically
    return os.path.join(bpy.utils.resource_path('USER'), "scripts", "presets", "operator")


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


class ExportlistProperties(bpy.types.PropertyGroup):
    list_visibility_settings: bpy.props.EnumProperty(
        name="List Entry",
        description="Select multiple options",
        items=[
            ('DEFAULT', "", "Status", 'OUTLINER_COLLECTION', 1),
            ('FILEPATH', "", "Filepath", 'FILE_FOLDER', 2),
            ('FILENAME', "", "Filename", 'FILE', 4),
            ('COLLECTION', "", "Settings", 'OPTIONS', 8),
            ('ROOT', "", "Root", 'EMPTY_ARROWS', 16),
            ('ORIGIN', "", "Origin option", 'OBJECT_ORIGIN', 32),
            ('FORMAT', "", "Format", 'FILE_LARGE', 64),
        ],
        options={'ENUM_FLAG'},  # This allows multi-select
        default={'DEFAULT'},
    )


class SIMPLE_EXPORT_menu_base:
    bl_label = ""

    def draw_header(self, context):
        layout = self.layout
        draw_simple_export_header(layout)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        # Draw Export Operators
        layout.label(text="Collection Operators")
        col = layout.column(align=True)
        from .shared_operator_call import call_assign_preset_op
        op = call_assign_preset_op(context, col)
        from .shared_operator_call import call_simple_export_path_ops
        op = call_simple_export_path_ops(context, col, outliner=False, individual_collection=False)
        from .shared_operator_call import call_create_export_collection_op
        op = call_create_export_collection_op(scene, col)

        # Draw Pre Export Operators List
        col.separator()

        draw_pre_export_operations(col, scene)

        # Draw Export Button
        row = col.row()
        row.scale_y = 2.0  # Adjust this value to change the height
        op = row.operator("simple_export.export_collections", text="Export Selected", icon='EXPORT')
        op.outliner = False
        op.individual_collection = False


class SimpleExportSettingsPanel(SIMPLE_EXPORT_menu_base, bpy.types.Panel):
    # bl_options = {'DEFAULT_CLOSED'}

    def draw_header(self, context):
        layout = self.layout
        draw_simple_export_header(layout, text="Simple Export Defaults")

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        draw_scene_settings_overwrite(context, layout, scene)


class VIEW3D_PT_SimpleExportMain(SimpleExportSettingsPanel):
    """Creates a Panel in the Object properties window"""

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Simple Export"
    bl_label = ""


class SimpleExportMainPanel(SIMPLE_EXPORT_menu_base, bpy.types.Panel):

    def draw_header(self, context):
        scene = context.scene
        layout = self.layout

        draw_simple_export_header(layout)

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        from .shared_draw import draw_exporter_presets
        draw_exporter_presets(layout)

        # draw Export List
        from .shared_draw import draw_export_list
        draw_export_list(layout, self.list_id, scene)

        # Draw Operator List
        super().draw(context)

        # draw_active_list_element(layout, context, scene)


class VIEW3D_PT_SimpleExportMain(SimpleExportMainPanel):
    """Creates a Panel in the Object properties window"""

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Simple Export"
    bl_label = ""

    list_id = "npanel"


class VIEW3D_PT_SimpleExportSettings(SimpleExportSettingsPanel):
    """Creates a Panel in the Object properties window"""
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Simple Export"
    bl_label = ""


class PROPERTIES_PT_SimpleExportMain(SimpleExportMainPanel):
    bl_idname = "PROPERTIES_PT_SimpleExportMain"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"

    list_id = "scene"


class PROPERTIES_PT_SimpleExportSettings(SimpleExportSettingsPanel):
    bl_idname = "PROPERTIES_PT_SimpleExportSettings"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"

    list_id = "scene"


class SIMPLE_EXPORT_MT_context_menu(bpy.types.Menu):
    bl_label = "Custom Collection Menu"
    bl_idname = "SIMPLE_EXPORT_MT_context_menu"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="Exporter Operations")
        row = layout.row()
        op = row.operator("scene.select_all_collections", text="Select All", icon="CHECKBOX_HLT")
        op.deselect = False
        row = layout.row()
        op = row.operator("scene.select_all_collections", text="Unselect All", icon="CHECKBOX_DEHLT")
        op.deselect = True


classes = (
    VIEW3D_PT_SimpleExportMain,
    VIEW3D_PT_SimpleExportSettings,
    PROPERTIES_PT_SimpleExportMain,
    PROPERTIES_PT_SimpleExportSettings,
    SIMPLE_EXPORT_MT_context_menu,
    ExportlistProperties,
)


def set_default_exportlist_properties(dummy):
    scene = bpy.context.scene
    # Set defaults for each PointerProperty
    if hasattr(scene, 'exportlist_nPanel_properties'):
        scene.exportlist_nPanel_properties.list_visibility_settings = {'DEFAULT'}
    if hasattr(scene, 'exportlist_popup_properties'):
        scene.exportlist_popup_properties.list_visibility_settings = {'DEFAULT', 'FILEPATH', 'ROOT', 'FORMAT'}
    if hasattr(scene, 'exportlist_scene_properties'):
        scene.exportlist_scene_properties.list_visibility_settings = {'DEFAULT', 'FILEPATH'}


# Register and Unregister
def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    bpy.types.Scene.exportlist_nPanel_properties = bpy.props.PointerProperty(type=ExportlistProperties)
    bpy.types.Scene.exportlist_scene_properties = bpy.props.PointerProperty(type=ExportlistProperties)
    bpy.types.Scene.exportlist_popup_properties = bpy.props.PointerProperty(type=ExportlistProperties)

    # Filter Properties
    bpy.types.Scene.use_filter = bpy.props.BoolProperty(
        name="Use Filter",
        description="Use filter for the export list",
        default=False
    )

    bpy.types.Scene.export_format_filter = bpy.props.EnumProperty(
        name="Export Format",
        description="Select the export format",
        items=get_export_format_items(),  # Dynamically generated items from EXPORT_FORMATS
        default='FBX',
    )

    # Register the handler
    bpy.app.handlers.load_post.append(set_default_exportlist_properties)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    del bpy.types.Scene.exportlist_nPanel_properties
    del bpy.types.Scene.exportlist_popup_properties

    # Remove the handler
    if set_default_exportlist_properties in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(set_default_exportlist_properties)
