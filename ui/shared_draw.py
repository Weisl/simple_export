# --- Draw Helpers ---
import textwrap

import bpy


def draw_collection_creation(context, layout):
    # Draw Create Button
    row = layout.row()
    from .shared_operator_call import call_create_export_collection_op
    call_create_export_collection_op(context, row)


def draw_parent_collection(context, layout):
    scene = context.scene
    layout.prop(scene, "parent_collection", text="Parent Collection")


def draw_export_preset_properties(layout, element):
    export_format = element.export_format  # Get the currently selected export format

    layout.label(text="Export Preset")

    # Find the property for the current export format
    prop_name = f"simple_export_preset_file_{export_format.lower()}"

    if hasattr(element, prop_name):
        layout.prop(element, prop_name, text='Preset')


    else:
        layout.label(text=f"No presets available for {export_format}", icon="ERROR")


def draw_collection_settings_properties(layout, element):
    layout.label(text="Collection Settings")

    layout.prop(element, "parent_collection")
    layout.prop(element, "collection_color")

    # Handle different property names between scene and preferences
    layout.prop(element, "collection_instance_offset")
    layout.prop(element, "use_root_object")

    if element.use_root_object and hasattr(element, "collection_set_root_offset_object"):
        layout.prop(element, "collection_set_root_offset_object")

    layout.prop(element, "set_preset")
    layout.prop(element, "set_export_path")


def draw_collection_name_properties(layout, element):
    layout.label(text="Collection Settings")
    layout.prop(element, "collection_prefix")
    layout.prop(element, "collection_suffix")
    layout.prop(element, "collection_blend_prefix")


def draw_export_filename_properties(layout, element):
    # Filename settings
    layout.label(text="File Name Settings")

    layout.prop(element, "filename_prefix")
    layout.prop(element, "filename_suffix")
    layout.prop(element, "filename_blend_prefix")


def draw_export_folderpath_properties(layout, element, is_preferences=False):
    layout.label(text="Export Path Mode")

    # Check if blend file is saved
    is_file_saved = bool(bpy.data.filepath)

    row = layout.row()
    row.prop(element, "export_folder_mode", expand=True)

    # Disable options that require a saved file
    if not is_file_saved:
        if not is_preferences:
            row.enabled = False
        layout.label(text="Save the blend file to use filepath modes", icon='INFO')

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
                op_btn = row.operator("file.external_operation", text='', icon='FILE_FOLDER')
                op_btn.operation = 'FOLDER_OPEN'
                op_btn.filepath = preview_path
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

    # Operator to open a folder
    folder_op = row.operator("file.external_operation", text='', icon='FILE_FOLDER')
    folder_op.operation = 'FOLDER_OPEN'
    from ..presets_addon.exporter_preset import simple_export_presets_folder
    folder_op.filepath = simple_export_presets_folder()
