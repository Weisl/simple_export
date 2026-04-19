import os

import bpy

from .. import __package__ as base_package
from ..core.export_formats import get_export_format_items
from ..core.info import ADDON_NAME


def draw_pre_export_operations(layout, target):
    """Draw pre-export operation toggles for a given target (CollectionPreExportOps or scene)."""
    col = layout.column(align=True)

    # Move to origin
    col.prop(target, 'move_by_collection_offset')

    # Triangulate
    col.prop(target, 'triangulate_before_export')

    # col.separator(factor=0.5)

    # Apply Transformation (subsumes scale + rotation when enabled)
    # col.prop(target, 'apply_transform_before_export')
    # sub = col.column(align=True)
    # sub.enabled = not target.apply_transform_before_export
    # sub.prop(target, 'apply_scale_before_export')
    # sub.prop(target, 'apply_rotation_before_export')

    # col.separator(factor=0.5)

    # Pre-rotate with configurable offset
    # col.prop(target, 'pre_rotate_objects')
    # if target.pre_rotate_objects:
    #     sub = col.column(align=True)
    #     sub.use_property_split = True
    #     sub.prop(target, 'pre_rotate_euler', text="Rotation Offset")


def draw_simple_export_header(layout, text="Simple Export"):
    row = layout.row(align=True)
    # Open documentation
    row.operator("wm.url_open", text="", icon="HELP").url = "https://weisl.github.io/exporter_overview/"
    # Open Preferences
    addon_name = ADDON_NAME
    op = row.operator("simple_export.open_preferences", text="", icon="PREFERENCES")
    op.addon_name = addon_name
    op.prefs_tabs = 'GENERAL'
    # Open Export Popup
    op = row.operator("wm.call_panel", text="", icon="WINDOW")
    op.name = "SIMPLE_EXPORT_PT_simple_export_popup"
    row.label(text=text)



def draw_active_list_element(layout, context, scene):
    # Ensure valid selection before showing details
    if 0 <= scene.collection_index < len(bpy.data.collections):
        selected_collection = bpy.data.collections[scene.collection_index]

        # Draw the panel header
        header, body = layout.panel(idname="ACTIVE_COL_PANEL", default_closed=False)
        header.label(text=f"Active Collection:", icon='OUTLINER_COLLECTION')

        if body:
            box = body.box()

            # Collection name and icon
            row = box.row(align=True)
            row.prop(selected_collection, 'name', icon='OUTLINER_COLLECTION')
            op = row.operator("simple_export.open_exporter_in_properties", text="",
                              icon='PROPERTIES')
            op.collection_name = selected_collection.name

            # User Group
            row = box.row(align=True)
            row.label(text="", icon='GROUP')
            group_name = getattr(selected_collection, 'export_group_name', '') or "No User Groups"
            row.menu("SIMPLE_EXPORT_MT_CollectionGroupMenu", text=group_name)

            if len(selected_collection.exporters) > 0:
                # Filepath
                row = box.row(align=True)
                row.prop(selected_collection, "simple_export_filepath_proxy", text="", expand=True)
                browse_op = row.operator("simple_export.collection_filepath_picker", text="", icon='FILE_FOLDER')
                browse_op.collection_name = selected_collection.name

                from .shared_operator_call import call_simple_export_path_ops
                op = call_simple_export_path_ops(context, row, text='', outliner=False,
                                                 individual_collection=True, collection_name=selected_collection.name)

                # Collection offset object
                root_box = box.box()

                row = root_box.row(align=True)
                icon = "LINKED" if selected_collection.use_root_object else "UNLINKED"
                if not selected_collection.use_root_object:
                    row.prop(selected_collection, "use_root_object", text="", icon=icon, toggle=True)
                else:
                    row.prop(selected_collection, "use_root_object", text='', icon=icon, toggle=True)
                row.label(text='Root Object')

                # root selection
                row = root_box.row(align=True)
                row.enabled = selected_collection.use_root_object
                row.prop(selected_collection, "root_object", text="")

                col = root_box.column(align=True)
                col.enabled = not selected_collection.use_root_object
                row = col.row(align=True)
                row.prop(selected_collection, "instance_offset", text='Collection Center')
                op = col.operator("object.set_collection_offset_cursor", text="Set Offset from Cursor")
                op.collection_name = selected_collection.name
                op = col.operator("object.set_collection_offset_object", text="Set Offset from Object")
                op.collection_name = selected_collection.name

                # Per-collection pre-export operations
                if hasattr(selected_collection, 'pre_export_ops'):
                    ops_header, ops_body = box.panel(idname="COL_PRE_EXPORT_OPS", default_closed=True)
                    ops_header.label(text="Pre-Export Operations")
                    if ops_body:
                        draw_pre_export_operations(ops_body, selected_collection.pre_export_ops)

                    box.separator()

                    ops_header, ops_body = box.panel(idname="COL_EXPORT_SETTINGS", default_closed=True)
                    ops_header.label(text="Exporter Settings")
                    if ops_body:
                        from .shared_operator_call import call_assign_preset_op
                        call_assign_preset_op(context, ops_body, individual_collection=True,
                                             collection_name=selected_collection.name)
                        ops_body.template_collection_exporters()

            else:
                box.label(text='No exporter configured', icon='INFO')
                from .shared_operator_call import call_simple_add_exporter_to_collection
                call_simple_add_exporter_to_collection(context, selected_collection, box)



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

    row = layout.row(align = True)
    icon = "LINKED" if collection.use_root_object else "UNLINKED"
    if not collection.use_root_object:
        row.prop(collection, "use_root_object", text="", icon=icon, toggle=True)
    else: 
        row.prop(collection, "use_root_object", text='', icon=icon, toggle=True)
    row.label(text='Root Object')

    row.prop(collection, "root_object", text="")



class ExportlistProperties(bpy.types.PropertyGroup):
    list_visibility_settings: bpy.props.EnumProperty(
        name="List Entry",
        description="Select multiple options",
        items=[
            ('FILEPATH', "", "Filepath", 'FILE_FOLDER', 1),
            ('ORIGIN', "", "Origin option", 'OBJECT_ORIGIN', 2),
            ('OPERATIONS', "", "Active Pre-Export Operations", 'MODIFIER',4),
            ('PRESET', "", "Preset", 'PRESET',8),
        ],
        options={'ENUM_FLAG'},  # This allows multi-select
        default={'FILEPATH', 'ORIGIN', 'PRESET'},
    )


class SIMPLE_EXPORT_menu_base:
    bl_label = ""

    def draw_header(self, context):
        layout = self.layout
        draw_simple_export_header(layout)

    def draw(self, context):
        layout = self.layout
        scene = context.scene


        col = layout.column(align=True)
        # Draw Export Button
        row = col.row()
        row.scale_y = 2.0  # Adjust this value to change the height
        op = row.operator("simple_export.export_collections", text="Export Selected", icon='EXPORT')
        op.outliner = False
        op.individual_collection = False




class SimpleExportMainPanel(SIMPLE_EXPORT_menu_base, bpy.types.Panel):

    def draw_header(self, context):
        scene = context.scene
        layout = self.layout

        draw_simple_export_header(layout)

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        from ..operators.version_check import update_available, latest_version_str

        if update_available:
            row = layout.row(align=True)
            row.alert = True
            row.label(text=f"Update available: v{latest_version_str}", icon='ERROR')


        from .shared_draw import draw_exporter_presets
        draw_exporter_presets(layout)

        # draw Export List
        from .shared_draw import draw_export_list
        draw_export_list(layout, self.list_id, scene)

        # Draw Operator List
        super().draw(context)

        draw_active_list_element(layout, context, scene)


class VIEW3D_PT_SimpleExportMain(SimpleExportMainPanel):
    """Creates a Panel in the Object properties window"""

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Simple Export"
    bl_label = ""

    list_id = "npanel"

    def draw(self, context):
        super().draw(context)
        self.layout.separator()
        self.layout.operator("simple_export.reload_addon", text="Reload Addon", icon='FILE_REFRESH')



class PROPERTIES_PT_SimpleExportMain(SimpleExportMainPanel):
    bl_idname = "PROPERTIES_PT_SimpleExportMain"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"

    list_id = "scene"

    @classmethod
    def poll(cls, context):
        prefs = context.preferences.addons[base_package].preferences
        return prefs.enable_output_panel



class SIMPLE_EXPORT_MT_context_menu(bpy.types.Menu):
    bl_label = "Custom Collection Menu"
    bl_idname = "SIMPLE_EXPORT_MT_context_menu"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        row.label(text="Exporter Operations")
        row = layout.row()
        op = row.operator("scene.select_all_collections", text="Select All")
        op.deselect = False
        row = layout.row()
        op = row.operator("scene.select_all_collections", text="Unselect All")
        op.deselect = True

        row = layout.row()
        op = row.operator("scene.expand_minimize_all_collections", text='Expand All')
        op.minimize = False
        row = layout.row()
        op = row.operator("scene.expand_minimize_all_collections", text='Minimize All',)
        op.minimize = True



        row = layout.row()
        from .shared_operator_call import call_assign_preset_op
        op = call_assign_preset_op(context, row)
        row = layout.row()
        from .shared_operator_call import call_simple_export_path_ops
        op = call_simple_export_path_ops(context, row, outliner=False, individual_collection=False)
        row = layout.row()
        from .shared_operator_call import call_create_export_collection_op
        op = call_create_export_collection_op(context.scene, row)
        



classes = (
    VIEW3D_PT_SimpleExportMain,
    PROPERTIES_PT_SimpleExportMain,
    SIMPLE_EXPORT_MT_context_menu,
    ExportlistProperties,
)


def set_default_exportlist_properties(dummy):
    scene = bpy.context.scene
    # Set defaults for each PointerProperty
    if hasattr(scene, 'exportlist_nPanel_properties'):
        scene.exportlist_nPanel_properties.list_visibility_settings = {'FILEPATH', 'ORIGIN', 'PRESET'}
    if hasattr(scene, 'exportlist_popup_properties'):
        scene.exportlist_popup_properties.list_visibility_settings = {'FILEPATH', 'ORIGIN', 'OPERATIONS'}
    if hasattr(scene, 'exportlist_scene_properties'):
        scene.exportlist_scene_properties.list_visibility_settings = {'FILEPATH', 'ORIGIN', 'PRESET'}



def get_filter_addon_preset_items(self, context):
    """Dynamic enum items: format presets and addon presets, matching the PRESET column display."""
    from ..presets_addon.exporter_preset import simple_export_presets_folder
    from ..core.export_formats import ExportFormats

    items = [('ALL', "All Presets", ""), ('NONE', "Missing Preset", "")]
    seen = set()

    # Addon presets as fallback values
    folder = simple_export_presets_folder()
    if os.path.isdir(folder):
        for fname in sorted(os.listdir(folder)):
            if fname.endswith('.py'):
                name = os.path.splitext(fname)[0]
                if name not in seen:
                    seen.add(name)
                    items.append((name, name, ""))

    return items


def get_filter_custom_group_items(self, context):
    """Dynamic enum items: all distinct non-empty export_group_name values."""
    groups = []
    seen = set()
    for col in bpy.data.collections:
        if col.exporters:
            name = getattr(col, 'export_group_name', '')
            if name and name not in seen:
                seen.add(name)
                groups.append(name)
    items = [('ALL', "All User Groups", ""), ('NONE', "No User Groups", "")]
    for g in sorted(groups):
        items.append((g, g, ""))
    return items


def get_filter_preset_export_items(self, context):
    """Dynamic enum items: all preset files available on disk."""
    from ..presets_export.preset_format_functions import get_preset_format_folder
    from ..core.export_formats import ExportFormats

    items = [('ALL', "All Presets", ""), ('NONE', "Missing Preset", "")]
    preset_folder = get_preset_format_folder()
    seen = set()

    for fmt in ExportFormats.all():
        subfolder_path = os.path.join(preset_folder, fmt.preset_subfolder)
        if not os.path.isdir(subfolder_path):
            continue
        for fname in sorted(os.listdir(subfolder_path)):
            if fname.endswith('.py'):
                name = os.path.splitext(fname)[0]
                if name not in seen:
                    seen.add(name)
                    items.append((name, name, ""))

    return items


# Register and Unregister
def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    bpy.types.Scene.exportlist_nPanel_properties = bpy.props.PointerProperty(type=ExportlistProperties)
    bpy.types.Scene.exportlist_scene_properties = bpy.props.PointerProperty(type=ExportlistProperties)
    bpy.types.Scene.exportlist_popup_properties = bpy.props.PointerProperty(type=ExportlistProperties)

    # Filter Properties
    bpy.types.Scene.filter_format = bpy.props.EnumProperty(
        name="Format",
        description="Filter collections by export format",
        items=[('ALL', "All Formats", "")] + get_export_format_items(),
        default='ALL',
    )

    bpy.types.Scene.filter_color_tag = bpy.props.EnumProperty(
        name="Color Tag",
        description="Filter collections by color tag",
        items=[
            ('ALL', "All Colors", ""),
            ('NONE', "No Color", "", 'OUTLINER_COLLECTION', 0),
            ('COLOR_01', "Red", "", 'COLLECTION_COLOR_01', 1),
            ('COLOR_02', "Orange", "", 'COLLECTION_COLOR_02', 2),
            ('COLOR_03', "Yellow", "", 'COLLECTION_COLOR_03', 3),
            ('COLOR_04', "Green", "", 'COLLECTION_COLOR_04', 4),
            ('COLOR_05', "Teal", "", 'COLLECTION_COLOR_05', 5),
            ('COLOR_06', "Blue", "", 'COLLECTION_COLOR_06', 6),
            ('COLOR_07', "Purple", "", 'COLLECTION_COLOR_07', 7),
            ('COLOR_08', "Pink", "", 'COLLECTION_COLOR_08', 8),
        ],
        default='ALL',
    )

    bpy.types.Scene.filter_selected_only = bpy.props.BoolProperty(
        name="Selected Only",
        description="Show only collections checked for export",
        default=False,
    )

    bpy.types.Scene.filter_name = bpy.props.StringProperty(
        name="Name",
        description="Filter collections by name (substring match)",
        default="",
    )

    bpy.types.Scene.filter_file_status = bpy.props.EnumProperty(
        name="File Status",
        description="Filter collections by export file status",
        items=[
            ('ALL', "All", ""),
            ('NEW', "Not Exported", "Only show collections that haven't been exported yet"),
            ('EXISTS', "Already Exported", "Only show collections with an existing output file"),
            ('LOCKED', "Locked", "Only show collections whose output file is read-only"),
            ('FAILED', "Export Failed", "Only show collections where the last export attempt failed"),
        ],
        default='ALL',
    )

    bpy.types.Scene.filter_directory = bpy.props.StringProperty(
        name="Directory",
        description="Filter by output directory",
        default='ALL',
    )

    bpy.types.Scene.filter_preset_addon_preset = bpy.props.EnumProperty(
        name="Addon Preset",
        description="Filter by last applied format export format preset",
        items=get_filter_addon_preset_items,
    )

    bpy.types.Scene.filter_custom_group = bpy.props.EnumProperty(
        name="Group",
        description="Filter collections by custom export group",
        items=get_filter_custom_group_items,
    )

    bpy.types.Scene.filter_preset_export_preset = bpy.props.EnumProperty(
        name="Addon Preset",
        description="Filter by the Simple Export addon preset used when configuring this collection",
        items=get_filter_preset_export_items,
    )

    bpy.types.Scene.sort_mode = bpy.props.EnumProperty(
        name="Sort",
        description="Sort the collection list",
        items=[
            ('NONE', "Default", ""),
            ('NAME', "Name", ""),
            ('FORMAT', "Format", ""),
            ('SELECTED_FIRST', "Selected First", ""),
            ('COLOR_TAG', "Color Tag", ""),
            ('PRESET', "Preset", ""),
        ],
        default='NONE',
    )

    bpy.types.Scene.sort_reverse = bpy.props.BoolProperty(
        name="Reverse",
        description="Reverse the sort order",
        default=False,
    )

    # Register the handler
    bpy.app.handlers.load_post.append(set_default_exportlist_properties)

    bpy.types.COLLECTION_PT_instancing.append(draw_custom_collection_ui)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)

    del bpy.types.Scene.exportlist_nPanel_properties
    del bpy.types.Scene.exportlist_popup_properties
    del bpy.types.Scene.filter_format
    del bpy.types.Scene.filter_color_tag
    del bpy.types.Scene.filter_selected_only
    del bpy.types.Scene.filter_name
    del bpy.types.Scene.filter_file_status
    del bpy.types.Scene.filter_directory
    del bpy.types.Scene.filter_preset_addon_preset
    del bpy.types.Scene.filter_custom_group
    del bpy.types.Scene.filter_preset_export_preset
    del bpy.types.Scene.sort_mode
    del bpy.types.Scene.sort_reverse

    # Remove the handler
    if set_default_exportlist_properties in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(set_default_exportlist_properties)

    bpy.types.COLLECTION_PT_instancing.remove(draw_custom_collection_ui)
