import bpy
import os
import textwrap

from ..core.info import COLOR_TAG_ICONS


class SIMPLEEXPORTER_OT_ShowCollectionError(bpy.types.Operator):
    """Show the last export error for a specific collection."""
    bl_idname = "simple_export.show_collection_error"
    bl_label = "Export Error"
    bl_description = "Show the last export error for this collection"

    collection_name: bpy.props.StringProperty()
    message: bpy.props.StringProperty()

    def invoke(self, context, event):
        results_str = context.window_manager.export_data_info
        results = eval(results_str) if results_str else []
        for r in results:
            if r['name'] == self.collection_name and not r['success']:
                self.message = r.get('message', '')
                break
        else:
            self.message = "No error record found for this collection."
        return context.window_manager.invoke_popup(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.label(text=self.collection_name, icon='CANCEL')
        layout.separator()
        col = layout.column(align=True)
        for line in textwrap.wrap(self.message, width=55) or [self.message]:
            col.label(text=line)
        layout.separator()
        op = layout.operator("simple_export.copy_to_clipboard", text="Copy Error", icon='COPYDOWN')
        op.text = self.message

    def execute(self, context):
        return {'FINISHED'}


class SIMPLEEXPORTER_OT_CopyExportReport(bpy.types.Operator):
    """Copy a full export report (all collections, status, filepath, message) to the clipboard."""
    bl_idname = "simple_export.copy_export_report"
    bl_label = "Copy Full Report"
    bl_description = "Copy a full export report to the clipboard"

    def execute(self, context):
        results_str = context.window_manager.export_data_info
        results = eval(results_str) if results_str else []

        if not results:
            self.report({'WARNING'}, "No export results to report")
            return {'CANCELLED'}

        lines = ["Export Report", "=" * 60]
        success_count = sum(1 for r in results if r['success'])
        fail_count = len(results) - success_count

        for r in results:
            status = "OK  " if r['success'] else "FAIL"
            filepath = r.get('filepath') or '-'
            message = r.get('message', '')
            lines.append(f"[{status}]  {r['name']}")
            lines.append(f"       Path:    {filepath}")
            if message:
                lines.append(f"       Message: {message}")

        lines.append("=" * 60)
        lines.append(f"Summary: {success_count} succeeded, {fail_count} failed")

        context.window_manager.clipboard = "\n".join(lines)
        self.report({'INFO'}, f"Report copied ({len(results)} entries)")
        return {'FINISHED'}


class SIMPLEEXPORTER_OT_CopyToClipboard(bpy.types.Operator):
    """Copy a message to the system clipboard."""
    bl_idname = "simple_export.copy_to_clipboard"
    bl_label = "Copy to Clipboard"
    bl_description = "Copy this message to the clipboard"

    text: bpy.props.StringProperty(name="Text", default="")

    def execute(self, context):
        context.window_manager.clipboard = self.text
        self.report({'INFO'}, "Copied to clipboard")
        return {'FINISHED'}


class SIMPLEEXPORTER_PT_PresetResultsPanel(bpy.types.Panel):
    """Panel to display the results of applying the preset."""
    bl_idname = "SIMPLEEXPORTER_PT_PresetResultsPanel"
    bl_label = "Preset Application Results"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 30

    def draw(self, context):
        layout = self.layout
        layout.label(text="Assign Export Format Presets:")

        # Get results from Scene
        results_str = context.window_manager.assign_preset_info_data
        results = eval(results_str) if results_str else []  # Parse results string into a list

        # Header row with column titles
        split = layout.split(factor=0.1)
        col_icon = split.column()  # Icon column
        col_name = split.column()  # Collection name column
        col_message = split.column()  # Info message column

        row = layout.row()
        col_icon.label(text="")
        col_name.label(text="Collection")
        col_message.label(text="Info")

        # Iterate over results and populate the table
        for result in results:
            split = layout.split(factor=0.05)  # Split for each row
            col_icon = split.column()
            col_name = split.column()
            col_message = split.column()

            # Icon Column
            col_icon.label(icon='CHECKMARK' if result['success'] else 'CANCEL')

            # Collection Name Column
            collection_name = result['name']
            collection = bpy.data.collections[collection_name]
            color_tag = collection.color_tag
            icon = COLOR_TAG_ICONS.get(color_tag, 'NONE')
            col_name.label(text=result['name'], icon=icon)

            # Info Message Column
            col_message.label(text=result['message'])


class SIMPLEEXPORTER_PT_FilePathResultsPanel(bpy.types.Panel):
    """Panel to display the results of applying the filepath."""
    bl_idname = "SIMPLEEXPORTER_PT_FilePathResultsPanel"
    bl_label = "Preset Application Results"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 30

    def draw(self, context):
        layout = self.layout
        layout.label(text="Filepath Result Preset:")

        # Get results from WindowManager
        results_str = context.window_manager.assign_filepath_result_info
        results = eval(results_str) if results_str else []  # Parse results string into a list

        # Header row with column titles
        split = layout.split(factor=0.1)
        col_icon = split.column()  # Icon column
        col_name = split.column()  # Collection name column
        col_message = split.column()  # Info message column

        row = layout.row()
        col_icon.label(text="")
        col_name.label(text="Collection")
        col_message.label(text="Filepath")

        # Iterate over results and populate the table
        for result in results:
            split = layout.split(factor=0.05)  # Split for each row
            col_icon = split.column()
            col_name = split.column()
            col_message = split.column()

            # Icon Column
            col_icon.label(icon='CHECKMARK' if result['success'] else 'CANCEL')

            # Collection Name Column
            collection_name = result['name']
            collection = bpy.data.collections[collection_name]
            color_tag = collection.color_tag

            icon = COLOR_TAG_ICONS.get(color_tag, 'NONE')
            col_name.label(text=result['name'], icon=icon)

            # Info Message Column
            if result['success']:
                # Info Message Column
                col_message.label(text=result['filepath'])
            else:
                col_message.label(text=result['message'])


# Popup to show export results
class SIMPLEEXPORTER_PT_ExportResultsPanel(bpy.types.Panel):
    """Panel to display the export results in a table format."""
    bl_idname = "SIMPLEEXPORTER_PT_ExportResultsPanel"
    bl_label = "Export Results"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 45

    def draw(self, context):
        layout = self.layout
        layout.label(text="Export Results:")

        # Column Sizes
        col1_split_fac = 0.04  # icon
        col2_split_fac = 0.20  # collection name
        col3_split_fac = 0.38  # filepath
        # remaining ~38% goes to info + copy button

        # Get results from WindowManager
        results_str = context.window_manager.export_data_info
        results = eval(results_str) if results_str else []  # Parse results string into a list

        # Header row with column titles
        split = layout.split(factor=col1_split_fac)
        col_icon = split.column()
        split = split.split(factor=col2_split_fac / (1.0 - col1_split_fac))
        col_name = split.column()
        split = split.split(factor=col3_split_fac / (1.0 - col2_split_fac))
        col_filepath = split.column()
        col_info = split.column()

        col_icon.label(text="")
        col_name.label(text="Collection")
        col_filepath.label(text="Filepath")
        col_info.label(text="Info")

        # Iterate over results and populate the table
        for result in results:
            split = layout.split(factor=col1_split_fac)
            col_icon = split.column()
            split = split.split(factor=col2_split_fac / (1.0 - col1_split_fac))
            col_name = split.column()
            split = split.split(factor=col3_split_fac / (1.0 - col2_split_fac))
            col_filepath = split.column()
            col_info = split.column()

            # Icon Column
            warnings = result.get('warnings', [])
            if not result['success']:
                status_icon = 'CANCEL'
            elif warnings:
                status_icon = 'ERROR'  # yellow triangle — succeeded with warnings
            else:
                status_icon = 'CHECKMARK'
            col_icon.label(icon=status_icon)

            # Collection Name Column
            col_name.label(text=result['name'])

            # Filepath Column
            col_filepath.label(text=result['filepath'] if 'filepath' in result else "-")

            # Info Message Column — main message + per-warning lines + copy button
            message = result.get('message', '')
            msg_row = col_info.row(align=True)
            msg_col = msg_row.column(align=True)
            for line in textwrap.wrap(message, width=40) or [message]:
                msg_col.label(text=line)
            for w in warnings:
                for line in textwrap.wrap(w, width=38) or [w]:
                    msg_col.label(text=f"! {line}")

            btn_col = msg_row.column(align=True)
            if not result['success']:
                copy_op = btn_col.operator("simple_export.copy_to_clipboard", text='', icon='COPYDOWN')
                copy_op.text = message

            if result['success'] and result.get('filepath'):
                export_dir = os.path.dirname(result['filepath'])
                btn_col.operator("wm.path_open", text='', icon='FILE_FOLDER').filepath = export_dir

        layout.separator()
        layout.operator("simple_export.copy_export_report", text="Copy Full Report", icon='COPYDOWN')


classes = (
    SIMPLEEXPORTER_OT_ShowCollectionError,
    SIMPLEEXPORTER_OT_CopyExportReport,
    SIMPLEEXPORTER_OT_CopyToClipboard,
    SIMPLEEXPORTER_PT_PresetResultsPanel,
    SIMPLEEXPORTER_PT_FilePathResultsPanel,
    SIMPLEEXPORTER_PT_ExportResultsPanel,
)


def register():
    bpy.types.WindowManager.export_data_info = bpy.props.StringProperty(default="[]")
    bpy.types.WindowManager.assign_filepath_result_info = bpy.props.StringProperty(default="[]")
    bpy.types.WindowManager.assign_preset_info_data = bpy.props.StringProperty(default="[]")

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)

    del bpy.types.WindowManager.export_data_info
    del bpy.types.WindowManager.assign_filepath_result_info
    del bpy.types.WindowManager.assign_preset_info_data
