# --- Draw Helpers ---
import textwrap

import bpy

from .. import __package__ as base_package


def get_table_columns(layout):
    split = layout.split(factor=0.25, align=True)
    split_left = split.column(align=True).split(factor=0.33, align=True)
    # Status
    col_01 = split_left.column(align=True)
    # Name
    col_02 = split_left.column(align=True)
    split_right = split.column(align=True).split(factor=0.95, align=True)  # Split the right side into 90% and 10%
    split_right_left = split_right.column(align=True).split(factor=0.5,
                                                            align=True)  # Split the 90% into two equal parts
    col_03 = split_right_left.column(align=True)
    col_04 = split_right_left.column(align=True)
    col_05 = split_right.column(align=True)  # This will be the very narrow column

    return col_01, col_02, col_03, col_04, col_05


def draw_parent_collection(context, layout):
    scene = context.scene
    layout.prop(scene, "parent_collection", text="Parent Collection")


def draw_export_preset_properties(layout, element):
    export_format = element.export_format  # Get the currently selected export format

    layout.label(text="Export Format Preset")

    # Find the property for the current export format
    prop_name = f"simple_export_preset_file_{export_format.lower()}"

    row = layout.row(align=True)
    if hasattr(element, prop_name):
        row.prop(element, prop_name, text='Preset')

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
    layout.prop(element, "use_root_object")
    layout.prop(element, "set_export_path")
    layout.prop(element, "assign_preset")


def draw_collection_name_properties(layout, element):
    layout.label(text="Collection Name")
    layout.prop(element, "collection_prefix")
    layout.prop(element, "collection_suffix")
    layout.prop(element, "collection_blend_prefix")


def draw_export_filename_properties(layout, element):
    # Filename settings
    layout.label(text="File Name")

    layout.prop(element, "filename_prefix")
    layout.prop(element, "filename_suffix")
    layout.prop(element, "filename_blend_prefix")


def draw_export_folderpath_properties(layout, element, is_preferences=False):
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

    # Disable options that require a saved file (Absolute paths don't need one)
    if not is_file_saved and element.export_folder_mode != 'ABSOLUTE':
        layout.label(text="Save the blend file to use this filepath modes", icon='INFO')

    if element.export_folder_mode == 'ABSOLUTE':
        layout.prop(element, "folder_path_absolute")
    if element.export_folder_mode == 'RELATIVE':
        layout.prop(element, "folder_path_relative")

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
    if buttons:
        add_op = row.operator(SceneExportPreset.bl_idname, text="", icon='ADD')
        remove_op = row.operator(SceneExportPreset.bl_idname, text="", icon='REMOVE')
        remove_op.remove_active = True

    # Pin button: shows PINNED when the current preset is the default, UNPINNED otherwise
    try:
        prefs = bpy.context.preferences.addons[base_package].preferences
        selected = bpy.context.scene.simple_export_selected_preset
        if selected and prefs.simple_export_default_preset == selected:
            row.label(text="", icon='PINNED')
        else:
            row.operator("simple_export.set_default_preset", text="", icon='UNPINNED')
    except Exception:
        pass

    # Operator to open a folder
    from ..presets_addon.exporter_preset import simple_export_presets_folder
    row.operator("wm.path_open", text='', icon='FILE_FOLDER').filepath = simple_export_presets_folder()


def draw_full_exporer_settings(layout, props):
    from ..ui.shared_draw import draw_export_fomrat

    # --- Export Format ---
    draw_export_fomrat(layout, props)

    # --- Collection Name ---
    box = layout.box()
    draw_collection_name_properties(box, props)

    # --- File Path ---
    box = layout.box()
    draw_export_folderpath_properties(box, props)

    # --- File Name ---
    box = layout.box()
    draw_export_filename_properties(box, props)

    # --- Preset Section ---
    box = layout.box()
    draw_export_preset_properties(box, props)

    # --- Collection Section ---
    box = layout.box()
    draw_collection_settings_properties(box, props)

    # --- Pre-Export Operations (defaults for new collections) ---
    box = layout.box()
    icon = 'WARNING_LARGE' if bpy.app.version >= (4, 3, 0) else 'ERROR'
    box.label(text="Pre-Export Operations (defaults for new collections)", icon=icon)
    from ..ui.export_panels import draw_pre_export_operations
    draw_pre_export_operations(box, props)


def draw_export_list(layout, list_id, scene):
    # === EXPORT TARGET (filters — above the list) ===
    box = layout.box()
    header_row = box.row(align=True)
    header_row.label(text="Export Target", icon='FILTER')
    header_row.operator("simple_export.clear_filters", text="Clear Filters")

    col = box.column(align=True)

    def filter_row(parent, label, prop, **kwargs):
        split = parent.split(factor=0.35, align=True)
        split.label(text=label)
        split.prop(scene, prop, text="", **kwargs)

    filter_row(col, "Format", "filter_format")
    filter_row(col, "Addon Preset", "filter_addon_preset")

    # User Group: menu with inline "Add New Group..." entry
    split = col.split(factor=0.35, align=True)
    split.label(text="User Group")
    current = scene.filter_custom_group
    if current == 'ALL':
        label = "All Groups"
    elif current == 'NONE':
        label = "No Group"
    else:
        label = current

    filter_row(col, "Directory", "filter_directory", icon='FILE_FOLDER')

    row = col.row(align=True)
    row.prop(scene, "filter_selected_only", text="", icon='CHECKBOX_HLT', toggle=True)
    row.prop(scene, "filter_name", text="", icon='VIEWZOOM')
    split.menu("SIMPLE_EXPORT_MT_FilterGroupMenu", text=label)


    more_header, more_body = col.panel(idname="EXPORT_TARGET_MORE_FILTERS", default_closed=True)
    more_header.label(text="More")
    if more_body:
        filter_row(more_body, "Color", "filter_color_tag")
        filter_row(more_body, "Status", "filter_file_status")
        filter_row(more_body, "Export Format Preset", "filter_preset")


    # === COLLECTION LIST ===
    row = layout.row()
    row.label(text="Simple Export Collection List")

    # Headers (popup only)
    factor = 0.97 if list_id == 'popup' else 0.9
    split = layout.split(factor=factor, align=True)
    main_column = split
    if list_id == 'popup':
        row = main_column.row(align=True)
        col_01, col_02, col_03, col_04, col_05 = get_table_columns(row)
        col_01.label(text="")
        col_02.label(text="Name")
        col_03.label(text="Filepath")
        col_04.label(text="Root")
        col_05.label(text="")

    # UIList
    factor = 0.97 if list_id == 'popup' else 0.9
    split = layout.split(factor=factor, align=True)
    main_column = split

    row = main_column.row(align=True)
    row.template_list("SCENE_UL_CollectionList", list_id, bpy.data, "collections", scene, "collection_index")

    narrow_column = split.column(align=True)
    col = narrow_column
    from .shared_operator_call import call_create_export_collection_op
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

