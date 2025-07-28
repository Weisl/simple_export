# --- Draw Helpers ---
import textwrap

import bpy


def draw_export_filename_properties(layout, element):
    layout.label(text="File Name")
    layout.prop(element, "filename_blend_prefix")
    layout.prop(element, "filename_prefix")
    layout.prop(element, "filename_suffix")


def draw_export_preset_properties(layout, element):
    layout.label(text="Export Preset")
    layout.prop(element, "set_preset")
    layout.prop(element, "preset_filepath")


def draw_collection_settings_properties(layout, element):
    layout.label(text="Collection Settings")
    layout.prop_search(element, "parent_collection_name", bpy.data, "collections")
    layout.prop(element, "collection_color")
    layout.prop(element, "collection_instance_offset")
    layout.prop(element, "use_root_object")


def draw_collection_name_properties(layout, element):
    layout.label(text="Collection Name")
    layout.prop(element, "collection_naming_overwrite")
    if element.collection_naming_overwrite:
        layout.prop(element, "collection_name_new")
        layout.prop(element, "use_numbering")
    layout.prop(element, "collection_blend_prefix")
    layout.prop(element, "collection_prefix")
    layout.prop(element, "collection_suffix")


def draw_export_filename_properties(layout, element):
    # Filename settings
    layout.label(text="File Name Settings")
    layout.prop(element, "filename_prefix")
    layout.prop(element, "filename_suffix")
    layout.prop(element, "filename_blend_prefix")


def draw_export_folderpath_properties(layout, element):
    layout.label(text="Export Path Mode")
    row = layout.row()
    row.prop(element, "export_folder_mode", expand=True)
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
