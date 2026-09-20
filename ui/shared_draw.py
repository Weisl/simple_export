# --- Draw Helpers ---
import textwrap

import bpy

from .. import __package__ as base_package
from ..core.info import ADDON_NAME


# Popup list column widths as fractions of the row: status, pre-export ops, name,
# filepath, root, actions. Must sum to 1.0.
POPUP_TABLE_COLUMN_WIDTHS = (0.06, 0.09, 0.15, 0.30, 0.30, 0.10)

# Icon-only buttons don't stretch to fill their column, so widen the pre-export
# toggles (and the matching header icons) explicitly to make them easy to hit.
POPUP_OPS_TOGGLE_SCALE_X = 1.6


def get_table_columns(layout):
    """Split `layout` into the popup list's columns (see POPUP_TABLE_COLUMN_WIDTHS)."""
    columns = []
    remaining = 1.0
    parent = layout
    for width in POPUP_TABLE_COLUMN_WIDTHS[:-1]:
        split = parent.split(factor=width / remaining, align=True)
        columns.append(split.column(align=True))
        parent = split.column(align=True)
        remaining -= width
    columns.append(parent)

    return tuple(columns)


def draw_parent_collection(context, layout):
    scene = context.scene
    layout.prop(scene, "parent_collection", text="Parent Collection")


def draw_export_preset_properties(layout, element, format_key=None, title="Export Format Preset", prop_text='Preset'):
    export_format = format_key or element.export_format  # Get the currently selected export format

    if title:
        layout.label(text=title)
    # Find the property for the current export format
    prop_name = f"simple_export_preset_file_{export_format.lower()}"

    row = layout.row(align=True)
    if hasattr(element, prop_name):
        row.prop(element, prop_name, text=prop_text)

    create_op = row.operator("simple_export.create_format_preset", text="", icon='ADD')
    create_op.export_format = export_format

    from ..presets_export.preset_format_functions import get_preset_format_folder
    folder_op = row.operator("wm.path_open", text='', icon='FILE_FOLDER')
    folder_op.filepath = get_preset_format_folder()

    ## Show the preset file path
    # from ..presets_export.preset_format_functions import get_format_preset_filepath
    # preset_file = get_format_preset_filepath(element, export_format)
    # layout.label(text=f"{preset_file}")

    return


def draw_collection_settings_properties(layout, element):
    layout.label(text="Collection Settings")

    layout.prop(element, "parent_collection")
    layout.prop(element, "collection_color")

    # Handle different property names between scene and preferences
    # layout.prop(element, "collection_instance_offset") # Not used at the moment.
    layout.prop(element, "set_export_path")
    layout.prop(element, "assign_preset")


def draw_root_object_properties(layout, element):
    """Root object defaults for new export collections (look is stored per export preset)."""
    from ..preferences.preferenecs import label_multiline

    layout.label(text="Root Object (defaults for new collections)")
    col = layout.column(align=True)
    label_multiline(
        context=bpy.context,
        text="Pivot empty that sets the collection's origin on export. "
             "Its look is stored with each export preset.",
        parent=col,
    )

    layout.prop(element, "use_root_object")

    col = layout.column(align=True)
    col.use_property_split = True
    col.prop(element, "root_empty_display_type", text="Shape")
    col.prop(element, "root_empty_display_size", text="Size")
    col.prop(element, "root_empty_show_name", text="Show Name")


def draw_collection_name_properties(layout, element):
    layout.label(text="Collection Name")
    layout.prop(element, "collection_prefix")
    layout.prop(element, "collection_separator")
    layout.prop(element, "collection_suffix")
    layout.prop(element, "collection_blend_prefix")


def draw_export_filename_properties(layout, element):
    # Filename settings
    layout.label(text="File Name")

    layout.prop(element, "filename_prefix")
    layout.prop(element, "filename_separator")
    layout.prop(element, "filename_suffix")
    layout.prop(element, "filename_blend_prefix")


def draw_export_folderpath_properties(layout, element):
    layout.label(text="Export Folder")

    # Check if blend file is saved
    is_file_saved = bool(bpy.data.filepath)

    row = layout.row()
    row.prop(element, "export_folder_mode", expand=True)

    # Determine context for operator
    context = None
    if element == bpy.context.preferences.addons[base_package].preferences:
        context = 'PREFS'
    elif element == bpy.context.scene:
        context = 'SCENE'

    # Warn when a saved file is required but the blend file hasn't been saved yet
    if not is_file_saved and element.export_folder_mode in ('RELATIVE', 'MIRROR'):
        layout.label(text="Blend file not saved \u2014 relative paths won't resolve at export time", icon='ERROR')

    if element.export_folder_mode == 'ABSOLUTE':
        layout.prop(element, "folder_path_absolute")
    if element.export_folder_mode == 'RELATIVE':
        row = layout.row(align=True)
        row.prop(element, "folder_path_relative")
        if context is not None:
            op = row.operator("simple_export.folder_path_relative_picker", text="", icon='FILE_FOLDER')
            op.use_relative_path = True
            op.context = context

    if element.export_folder_mode == 'MIRROR':
        layout.prop(element, "folder_path_search", text="Search Path")
        layout.prop(element, "folder_path_replace", text="Replacement Path")
        try:
            from ..preferences.preferenecs import compute_mirror_preview
            preview_path = compute_mirror_preview(element)
            layout.label(text="Export Folder Preview:")
            row = layout.row(align=True)
            row.label(text=preview_path)
            import os
            if os.path.exists(preview_path):
                bpy.ops.wm.path_open(filepath=preview_path)
        except Exception:
            pass


def label_multiline(context, text, parent):
    chars = int(context.region.width / 7)  # 7 pix on 1 character
    wrapper = textwrap.TextWrapper(width=chars)
    text_lines = wrapper.wrap(text=text)
    for text_line in text_lines:
        parent.label(text=text_line)


def draw_export_fomrat(layout, elment):
    layout.prop(elment, "export_format", text="Format")


def draw_exporter_presets(layout, buttons=False):
    """
    Draw the naming presets menu in the layout.
    Args:
        layout (UILayout): The UI layout.
        preset_context (str): The context type for the preset operations.
    """
    row = layout.row(align=True)

    from ..presets_addon.exporter_preset import EXPORT_MT_scene_presets, \
        SceneExportPreset

    # Determine the appropriate preset menu and operators based on the context
    row.menu(EXPORT_MT_scene_presets.__name__, text=EXPORT_MT_scene_presets.bl_label)

    # + button: opens preferences on the Presets tab to create/manage presets
    new_op = row.operator("simple_export.open_preferences", text="", icon='ADD')
    new_op.addon_name = ADDON_NAME
    new_op.prefs_tabs = 'SETTINGS'

    if buttons:
        row.operator(SceneExportPreset.bl_idname, text="", icon='ADD')
        remove_op = row.operator(SceneExportPreset.bl_idname, text="", icon='REMOVE')
        remove_op.remove_active = True

    # Operator to open a folder
    from ..presets_addon.exporter_preset import simple_export_presets_folder
    row.operator("wm.path_open", text='', icon='FILE_FOLDER').filepath = simple_export_presets_folder()


def draw_full_exporer_settings(layout, props):
    """The settings of one export preset, one plain box per group of settings."""
    from ..ui.export_panels import draw_pre_export_operations

    # --- Format and its native options file ---
    box = layout.box()
    col = box.column(align=True)
    draw_export_fomrat(col, props)
    draw_export_preset_properties(col, props, title=None, prop_text="Format Options")

    # --- Export Folder ---
    draw_export_folderpath_properties(layout.box(), props)

    # --- Naming: file and collection names are the two sub-groups ---
    box = layout.box()
    box.label(text="Naming")
    draw_export_filename_properties(box.box(), props)
    draw_collection_name_properties(box.box(), props)

    # --- Collection ---
    draw_collection_settings_properties(layout.box(), props)

    # --- Root Object ---
    draw_root_object_properties(layout.box(), props)

    # --- Pre-Export Operations ---
    box = layout.box()
    box.label(text="Pre-Export Operations (defaults for new collections)")
    draw_pre_export_operations(box, props)


def draw_export_list(layout, list_id, scene):
    # === PROMINENT ADD BUTTON (not needed in the export popup) ===
    from .shared_operator_call import call_create_export_collection_op
    if list_id != 'popup':
        row = layout.row(align=True)
        row.scale_y = 1.5
        call_create_export_collection_op(scene, row, icon='ADD', text="Create Export Collection")

    # === EXPORT TARGET (filters — above the list) ===
    box = layout.box()
    header_row, filters_body = box.panel(idname="EXPORT_TARGET_FILTERS", default_closed=True)
    header_row.label(text="Export Target", icon='FILTER')
    header_row.operator("simple_export.clear_filters", text="Clear Filters")

    if filters_body:
        col = filters_body.column(align=True)

        def filter_row(parent, label, prop, **kwargs):
            split = parent.split(factor=0.35, align=True)
            split.label(text=label)
            split.prop(scene, prop, text="", **kwargs)

        filter_row(col, "Addon Preset", "filter_preset_addon_preset")
        filter_row(col, "Format", "filter_format")

        # User Group: menu with inline "Add New Group..." entry
        split = col.split(factor=0.35, align=True)
        split.label(text="User Group")
        current = scene.filter_custom_group
        if current == 'ALL':
            label = "All User Groups"
        elif current == 'NONE':
            label = "No User Groups"
        else:
            label = current

        dir_split = col.split(factor=0.35, align=True)
        dir_split.label(text="Directory")
        current_dir = scene.filter_directory
        if current_dir == 'ALL':
            dir_label = "All Directories"
        elif current_dir == 'NO_PATH':
            dir_label = "No Directory"
        else:
            dir_label = current_dir
        dir_split.menu("SIMPLE_EXPORT_MT_FilterDirectoryMenu", text=dir_label)

        row = col.row(align=True)
        row.prop(scene, "filter_selected_only", text="", icon='CHECKBOX_HLT', toggle=True)
        row.prop(scene, "filter_name", text="", icon='VIEWZOOM')
        split.menu("SIMPLE_EXPORT_MT_FilterGroupMenu", text=label)

        more_header, more_body = col.panel(idname="EXPORT_TARGET_MORE_FILTERS", default_closed=True)
        more_header.label(text="More")
        if more_body:
            col = more_body.column(align=True)
            filter_row(col, "Color", "filter_color_tag")
            filter_row(col, "Status", "filter_file_status")
            filter_row(col, "Export Format Preset", "filter_preset_export_preset")


    # === COLLECTION LIST ===
    row = layout.row()
    row.label(text="Simple Export Collection List")

    # Headers (popup only)
    factor = 0.97 if list_id == 'popup' else 0.9
    split = layout.split(factor=factor, align=True)
    main_column = split
    if list_id == 'popup':
        row = main_column.row(align=True)
        col_status, col_ops, col_name, col_path, col_root, col_actions = get_table_columns(row)
        col_status.label(text="")
        # Icons mirror the pre-export toggles in each row
        ops_row = col_ops.row(align=True)
        ops_row.scale_x = POPUP_OPS_TOGGLE_SCALE_X
        ops_row.label(text="", icon='OBJECT_ORIGIN')
        ops_row.label(text="", icon='MOD_TRIANGULATE')
        col_name.label(text="Name")
        col_path.label(text="Filepath")
        col_root.label(text="Root")
        col_actions.label(text="")

    # UIList
    factor = 0.97 if list_id == 'popup' else 0.9
    split = layout.split(factor=factor, align=True)
    main_column = split

    row = main_column.row(align=True)
    row.template_list("SCENE_UL_CollectionList", list_id, bpy.data, "collections", scene, "collection_index")

    narrow_column = split.column(align=True)
    col = narrow_column
    if list_id != 'popup':
        call_create_export_collection_op(scene, col, icon='ADD', text="")
        col.separator()
    col.menu("SIMPLE_EXPORT_MT_context_menu", icon='DOWNARROW_HLT', text="")

    col.separator()
    if list_id == 'npanel':
        visibility_properties = scene.exportlist_nPanel_properties
        col.prop(visibility_properties, "list_visibility_settings")

    if list_id == 'scene':
        visibility_properties = scene.exportlist_scene_properties
        col.prop(visibility_properties, "list_visibility_settings")

    row = layout.row(align=True)
    row.operator("scene.select_all_collections", text='All', icon='CHECKBOX_HLT').deselect = False
    row.operator("scene.select_all_collections", text='None', icon='CHECKBOX_DEHLT').deselect = True
    op = row.operator("scene.expand_minimize_all_collections", text='Expand', icon='TRIA_DOWN')
    op.minimize = False
    op = row.operator("scene.expand_minimize_all_collections", text='Mnimize', icon='TRIA_UP')
    op.minimize = True


