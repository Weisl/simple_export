# --- Draw Helpers ---
import textwrap


def draw_operator_filepath_settings(layout, op):
    layout.label(text="Export Path Mode")
    row = layout.row()
    row.prop(op, "export_folder_mode", expand=True)
    if op.export_folder_mode == 'ABSOLUTE':
        layout.prop(op, "folder_path_absolute")
    if op.export_folder_mode == 'RELATIVE':
        layout.prop(op, "folder_path_relative")
    if op.export_folder_mode == 'MIRROR':
        layout.prop(op, "folder_path_search", text="Search Path")
        layout.prop(op, "folder_path_replace", text="Replacement Path")
        try:
            from ..preferences.preferenecs import compute_mirror_preview
            preview_path = compute_mirror_preview(op)
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
