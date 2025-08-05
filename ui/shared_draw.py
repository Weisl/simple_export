# --- Draw Helpers ---
import textwrap

import bpy

from .. import __package__ as base_package


def draw_export_preset_properties(layout, element):
    scene = bpy.context.scene
    prefs = bpy.context.preferences.addons[base_package].preferences
    export_format = scene.export_format  # Get the currently selected export format

    layout.label(text="Export Preset")

    if scene.overwrite_preset_settings:
        set = scene
        label = 'Preset'
    else:  # scene.overwrite_preset_settings:
        layout.enabled = False
        set = prefs
        label = 'Default Preset'

    # Use the same approach as preferences - iterate through all formats

    # Find the property for the current export format
    prop_name = f"simple_export_preset_file_{export_format.lower()}"

    if hasattr(set, prop_name):
        layout.prop(set, prop_name, text=label)
    else:
        layout.label(text=f"No presets available for {export_format}", icon="ERROR")


def draw_collection_settings_properties(layout, element):
    layout.label(text="Collection Settings")
    # Check if this is a scene object (has parent_collection_name) or preferences object
    if hasattr(element, "parent_collection_name"):
        layout.prop_search(element, "parent_collection_name", bpy.data, "collections")
    layout.prop(element, "collection_color")

    # Handle different property names between scene and preferences
    if hasattr(element, "collection_instance_offset"):
        layout.prop(element, "collection_instance_offset")
    if hasattr(element, "collection_set_location_offset_on_creation"):
        layout.prop(element, "collection_set_location_offset_on_creation")

    if hasattr(element, "use_root_object"):
        layout.prop(element, "use_root_object")
    if hasattr(element, "collection_use_root_offset_object"):
        layout.prop(element, "collection_use_root_offset_object")
        if element.collection_use_root_offset_object and hasattr(element, "collection_set_root_offset_object"):
            layout.prop(element, "collection_set_root_offset_object")

    layout.prop(element, "set_preset")
    layout.prop(element, "set_export_path")


def draw_collection_name_properties(layout, element):
    layout.label(text="Collection Name")

    if getattr(element, "collection_naming_overwrite", None):
        layout.prop(element, "collection_naming_overwrite")
        if element.collection_naming_overwrite:
            layout.prop(element, "collection_name_new")
            layout.prop(element, "use_numbering")

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
