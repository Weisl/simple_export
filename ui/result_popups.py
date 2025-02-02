import bpy
import os

from ..core.info import COLOR_TAG_ICONS


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
    bl_ui_units_x = 30

    def draw(self, context):
        layout = self.layout
        layout.label(text="Export Results:")

        # Column Sizes
        col1_split_fac = 0.05  # Adjust for first column width
        col2_split_fac = 0.25  # Adjust for second column width
        col3_split_fac = 0.45  # Adjust for filepath column width
        col4_split_fac = 0.25  # Remaining for the info column

        # Get results from WindowManager
        results_str = context.window_manager.export_data_info
        results = eval(results_str) if results_str else []  # Parse results string into a list

        # Header row with column titles
        split = layout.split(factor=col1_split_fac)
        col_icon = split.column()  # Icon column
        split = split.split(factor=col2_split_fac / (1.0 - col1_split_fac))  # Normalize remaining space
        col_name = split.column()  # Collection name column
        split = split.split(factor=col3_split_fac / (1.0 - col2_split_fac))
        col_filepath = split.column()  # Filepath column
        col_info = split.column()  # Info message column

        header_row = layout.row()
        header_row.alignment = 'CENTER'
        col_icon.label(text="")  # Icon column title (empty for icons)
        col_name.label(text="Collection")  # Collection name column title
        col_filepath.label(text="Filepath")  # Filepath column title
        col_info.label(text="Info")  # Info message column title

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
            col_icon.label(icon='CHECKMARK' if result['success'] else 'CANCEL')

            # Collection Name Column
            col_name.label(text=result['name'])

            # Filepath Column
            col_filepath.label(text=result['filepath'] if 'filepath' in result else "-")

            # Info Message Column
            row = col_info.row(align=True)
            row.label(text=result['message'])

            if result['success']:
                op = row.operator("file.external_operation", text='', icon='FILE_FOLDER')
                op.operation = 'FOLDER_OPEN'
                export_dir = os.path.dirname(result['filepath'])
                op.filepath = export_dir


classes = (
    SIMPLEEXPORTER_PT_FilePathResultsPanel,
    SIMPLEEXPORTER_PT_ExportResultsPanel
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
