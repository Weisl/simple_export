import os

import bpy

from .collection_utils import update_collection_offset
from .functions import ensure_export_folder_exists, apply_collection_offset


def recursiceLayerCollection(layerColl, collName):
    # print(f"Checking collection: {layerColl.name}")  # Debug print
    if layerColl.name == collName:
        # print(f"Found collection: {collName}")  # Debug print
        return layerColl
    for layer in layerColl.children:
        found = recursiceLayerCollection(layer, collName)
        if found:
            return found
    return None


def set_active_layer_Collection(collection_name):
    # Switching active Collection to active Object selected
    layer_collection = bpy.context.view_layer.layer_collection
    layerColl = recursiceLayerCollection(layer_collection, collection_name)
    bpy.context.view_layer.active_layer_collection = layerColl


def generate_export_path(collection_name, export_format, export_dir, search_path, replacement_path):
    """
    Set the export path for a given collection's exporter.

    Args:
        collection_name (str): The name of the collection.
        exporter_dir (str): Path to the export folder.
        search_path (str): The original path to be replaced.
        replacement_path (str): The replacement path to be applied.
    """

    export_name = collection_name
    from .panels import EXPORT_FORMATS
    export_extension = EXPORT_FORMATS[export_format]["file_extension"]
    export_name += f".{export_extension}"  # or use prefs.export_format to determine extension
    export_path = os.path.join(export_dir, export_name)

    if search_path in export_path:
        export_path = export_path.replace(search_path, replacement_path)
    return export_path


def assign_exporter_path(exporter, export_path):
    ensure_export_folder_exists(export_path)

    if not exporter:
        msg = "No valid exporter found"
        return False, msg

    if not export_path:
        msg = "Please select a Preset"
        return False, msg

    # Apply the properties to the exporter
    exporter.export_properties.filepath = export_path

    return True, None


def temporarily_disable_offset_handler():
    """Temporarily removes the collection offset update handler."""
    if update_collection_offset in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_collection_offset)


def reenable_offset_handler():
    """Re-enables the collection offset update handler."""
    if update_collection_offset not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(update_collection_offset)


def call_export_popup(export_results, context):
    """Handle cancellation with results."""
    # Store results in WindowManager
    context.window_manager.export_data_info = str(export_results)

    bpy.ops.wm.call_panel(name="SIMPLEEXPORTER_PT_ExportResultsPanel")
    return {'CANCELLED'}


def show_results(export_results):
    """Display the export results."""
    bpy.ops.simple_export.results_popup('INVOKE_DEFAULT', export_results=str(export_results))
    return {'FINISHED'}


def validate_collection(collection_name):
    """Validate the collection and return it if valid."""
    if not collection_name or not bpy.data.collections.get(collection_name):
        return None  # Return None for invalid collections
    return bpy.data.collections.get(collection_name)


def find_exporter(collection, export_format):
    from .panels import EXPORT_FORMATS
    """Find the appropriate exporter for the given collection and format."""
    for exporter in collection.exporters:
        if str(type(exporter.export_properties)) == EXPORT_FORMATS[export_format]["op_type"]:
            return exporter
    return None  # Return None if no valid exporter is found


def get_exporter_id(self, collection, exporter):
    """Get the exporter ID within the collection."""
    for idx, exp in enumerate(collection.exporters):
        if exp == exporter:
            return idx
    raise ValueError(f"{exporter.name} not found in the exporters of collection '{self.collection_name}'.")


def add_extension(path, export_format):
    from .panels import EXPORT_FORMATS
    file_extension = EXPORT_FORMATS[export_format]["file_extension"]

    # Check if the filename already has the extension
    if not path.lower().endswith(path.lower()):
        path += file_extension

    return path


def is_really_absolute(path):
    return os.path.abspath(path) == path


def clean_relative_path(path):
    """
    Convert relative paths (//) to absolute paths and normalize them.
    Ensures paths are correctly interpreted across different operating systems.
    """

    # Convert Blender relative paths (//) or root-relative paths (\..) to absolute
    if not is_really_absolute(path):
        path = bpy.path.abspath(path)

    # Normalize path to clean up redundant separators (e.g., \\, //)
    path = os.path.normpath(path)

    return path


def pre_export_checks(export_path):
    """Perform pre-export checks and return file existence and timestamp."""

    file_exists = os.path.exists(export_path)
    file_timestamp = os.path.getmtime(export_path) if file_exists else None
    ensure_export_folder_exists(export_path)
    return file_exists, file_timestamp


def post_export_checks(export_path, file_exists_before, file_timestamp_before):
    """Validate the exported file."""
    if not export_path:
        return False, f"No filepath specified."
    if not os.path.exists(export_path):
        return False, f"File was not created."
    if not os.access(export_path, os.W_OK):
        return False, f"File is read-only."
    # if file_exists_before and os.path.getmtime(export_path) <= file_timestamp_before:
    #     return False, f"File was not updated."
    return True, f"Export successful."


def get_outliner_collections(context):
    # Get all selected items in the outliner
    selected_ids = context.selected_ids

    return [item for item in selected_ids if isinstance(item, bpy.types.Collection)]


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

            from .uilist import color_tag_icons
            icon = color_tag_icons.get(color_tag, 'NONE')
            col_name.label(text=result['name'], icon=icon)

            # Info Message Column
            col_message.label(text=result['filepath'])


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


class SCENE_OT_SelectAllCollections(bpy.types.Operator):
    bl_idname = "scene.select_all_collections"
    bl_label = "Select All Collections"
    bl_options = {'REGISTER', 'UNDO'}

    invert: bpy.props.BoolProperty()

    def execute(self, context):
        for collection in bpy.data.collections:
            collection.simple_export_selected = not self.invert
        return {'FINISHED'}


class SCENE_OT_SetExporterPath(bpy.types.Operator):
    """
    Operator to set the exporter path for a collection based on the original and replacement paths defined in the scene properties.
    """
    bl_idname = "scene.set_export_path"
    bl_label = "Set Export Path"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)

        prefs = bpy.context.preferences.addons[__package__].preferences
        wm = context.window_manager
        settings_col = wm if wm.overwrite_collection_settings else prefs
        settings_filepath = wm if wm.overwrite_filepath_settings else prefs

        if not settings_filepath.use_custom_export_folder:
            blend_filepath = bpy.data.filepath
            # Return if Blend File hasn't been saved
            if not blend_filepath:
                self.report({'ERROR'}, f"Save the Blend file before calling this operator.")
                return {'CANCELLED'}
            export_dir = os.path.dirname(blend_filepath)
        else:
            export_dir = settings_filepath.custom_export_path

        # Return if collection not found
        if not collection:
            self.report({'ERROR'}, f"Collection '{self.collection_name}' not found.")
            return {'CANCELLED'}

        # Path variables
        search_path = settings_filepath.search_path
        replacement_path = settings_filepath.replacement_path

        # Add custom exporter
        exporter = find_exporter(collection, wm.export_format)

        # Return
        if not exporter:
            self.report({'ERROR'}, f"Could not add exporter to collection '{collection.name}'.")
            return {'CANCELLED'}

        # Set export Path
        export_format = wm.export_format
        export_path = generate_export_path(collection.name, export_format, export_dir, search_path, replacement_path)
        success, msg = assign_exporter_path(exporter, export_path)

        self.report({'INFO'}, f"Export path set to {export_path}")
        return {'FINISHED'}

    def get_custom_exporter_for_collection(self, collection_name, exporter_name):
        """
        Retrieve the custom exporter for a given collection.

        Args:
            collection_name (str): The name of the collection.
            exporter_name (str): The name of the exporter.

        Returns:
            bpy.types.PropertyGroup or None: The exporter if found, otherwise None.
        """
        collection = bpy.data.collections.get(collection_name)
        if not collection:
            return None

        for exporter in collection.exporters:
            if exporter.name == exporter_name:
                return exporter

        return None


class SCENE_OT_SetExporterPathSelection(bpy.types.Operator):
    """
    Operator to set the exporter path for a collection based on the original and replacement paths defined in the scene properties.
    """
    bl_idname = "scene.set_export_path_selection"
    bl_label = "Set Export Path"
    bl_options = {'REGISTER', 'UNDO'}

    outliner: bpy.props.BoolProperty()

    def execute(self, context):
        results = []  # To store the renaming status of each collection
        prefs = bpy.context.preferences.addons[__package__].preferences
        wm = context.window_manager
        settings_col = wm if wm.overwrite_collection_settings else prefs
        settings_filepath = wm if wm.overwrite_filepath_settings else prefs

        collection_list = bpy.data.collections
        if self.outliner:
            collection_list = get_outliner_collections(context)

        for collection in collection_list:
            try:
                # return early
                if not collection.simple_export_selected or len(collection.exporters) == 0:
                    continue

                # Validate collection
                collection = validate_collection(collection.name)
                if not collection:
                    continue

                set_active_layer_Collection(collection.name)

                # Find and validate exporter
                exporter = find_exporter(collection, wm.export_format)

                if not exporter:
                    continue

                if settings_filepath.use_custom_export_folder:
                    if not settings_filepath.custom_export_path:
                        raise ValueError("Invalid Export Path.")

                    export_dir = settings_filepath.custom_export_path
                else:
                    # Return if Blend File hasn't been saved
                    if not bpy.data.filepath:
                        raise ValueError("Save the Blend file before calling this operator.")
                    export_dir = os.path.dirname(bpy.data.filepath)

                # Path variables
                search_path = settings_filepath.search_path
                replacement_path = settings_filepath.replacement_path

                export_path = generate_export_path(collection.name, wm.export_format, export_dir, search_path,
                                                   replacement_path)
                success, msg = assign_exporter_path(exporter, export_path)
                results.append({'name': collection.name, 'success': success, 'filepath': export_path, 'message': msg})

            except Exception as e:
                # Handle per-collection errors
                results.append({'name': collection.name, 'success': False, 'filepath': export_path, 'message': str(e)})

        # Store results in WindowManager
        context.window_manager.assign_filepath_result_info = str(results)
        # Show results in the panel
        bpy.ops.wm.call_panel(name="SIMPLEEXPORTER_PT_FilePathResultsPanel")

        return {'FINISHED'}


class SCENE_OT_ExportCollection(bpy.types.Operator):
    """
    Operator to export a single collection with post-export validations and results popup.
    """

    bl_idname = "simple_export.export_collection"
    bl_label = "Export Collection"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        export_results = []
        temporarily_disable_offset_handler()
        success = False

        prefs = bpy.context.preferences.addons[__package__].preferences
        wm = context.window_manager
        settings_col = wm if wm.overwrite_collection_settings else prefs
        settings_filepath = wm if wm.overwrite_filepath_settings else prefs

        try:
            # Validate collection
            collection = validate_collection(self.collection_name)
            set_active_layer_Collection(collection.name)

            # Find and validate exporter
            exporter = find_exporter(collection, wm.export_format)
            exporter_id = get_exporter_id(self, collection, exporter)

            # Pre-export checks
            export_path = add_extension(exporter.export_properties.filepath, wm.export_format)
            export_path = clean_relative_path(export_path)
            print('EXPORT PATH: ' + str(export_path))

            file_exists_before, file_timestamp_before = pre_export_checks(export_path)

            # Apply instance offset if enabled
            if wm.move_to_origin:
                apply_collection_offset(collection)

            # Perform the export
            bpy.ops.collection.exporter_export(index=exporter_id)

            # Post-export validation
            success, message = post_export_checks(export_path, file_exists_before, file_timestamp_before)
            export_results.append(
                {'name': collection.name, 'success': success, 'filepath': export_path, 'message': message})

        except Exception as e:
            # Handle errors in one place
            export_results.append(
                {'name': self.collection_name or "Unknown Collection", 'success': False, 'filepath': export_path,
                 'message': str(e)})

        finally:
            if wm.move_to_origin:
                # Revert instance offset and show results
                apply_collection_offset(collection, inverse=True)

        if success:
            self.report({'INFO'}, f"Export Sucessful")

            # Always show export infos
            if not prefs.report_errors_only:
                call_export_popup(export_results, context)

            return {'FINISHED'}

        else:
            self.report({'ERROR'}, f"Export failed")
            call_export_popup(export_results, context)
            return {'CANCELLED'}


# Operator to export selected collections
class SCENE_OT_ExportCollectionsSelection(bpy.types.Operator):
    bl_idname = "simple_export.export_selected_collections"
    bl_label = "Export Selected"
    bl_options = {'REGISTER', 'UNDO'}

    outliner: bpy.props.BoolProperty()

    def execute(self, context):
        export_results = []
        export_collections = []
        temporarily_disable_offset_handler()
        error_count = 0

        prefs = bpy.context.preferences.addons[__package__].preferences
        wm = context.window_manager
        settings_col = wm if wm.overwrite_collection_settings else prefs
        settings_filepath = wm if wm.overwrite_filepath_settings else prefs

        collection_list = bpy.data.collections

        if self.outliner:
            collection_list = get_outliner_collections(context)

        for collection in collection_list:
            try:
                # return early
                if not collection.simple_export_selected or len(collection.exporters) == 0:
                    continue

                # Validate collection
                collection = validate_collection(collection.name)
                if not collection:
                    continue

                set_active_layer_Collection(collection.name)

                # Find and validate exporter
                exporter = find_exporter(collection, wm.export_format)

                if not exporter:
                    continue

                exporter_id = get_exporter_id(self, collection, exporter)

                # Pre-export checks
                export_path = add_extension(exporter.export_properties.filepath, wm.export_format)
                export_path = clean_relative_path(export_path)

                file_exists_before, file_timestamp_before = pre_export_checks(export_path)

                # Apply instance offset if enabled
                if wm.move_to_origin:
                    apply_collection_offset(collection)

                export_collections.append(collection)

                # Perform the export
                bpy.ops.collection.exporter_export(index=exporter_id)

                # Post-export validation
                success, message = post_export_checks(export_path, file_exists_before, file_timestamp_before)
                export_results.append(
                    {'name': collection.name, 'success': success, 'filepath': export_path, 'message': message})
                if not success:
                    error_count += 1


            except Exception as e:
                # Handle errors in one place
                export_results.append(
                    {'name': self.collection_name or "Unknown Collection", 'success': False, 'filepath': export_path,
                     'message': str(e)})

            finally:
                if wm.move_to_origin:
                    apply_collection_offset(collection, inverse=True)

        if error_count == 0:
            self.report({'INFO'}, f"Export Sucessful")
            # Always show export infos
            if not prefs.report_errors_only:
                call_export_popup(export_results, context)

            return {'FINISHED'}

        else:
            self.report({'WARNING'}, f"Export with Errors: See Result windows or console for further information.")
            call_export_popup(export_results, context)
            return {'CANCELLED'}


class SCENE_OT_OpenExportDirectory(bpy.types.Operator):
    """
    Operator to open the export directory of the currently selected collection in the file explorer.
    """
    bl_idname = "scene.open_export_directory"
    bl_label = "Open Export Directory"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if not collection or len(collection.exporters) == 0:
            self.report({'WARNING'}, "No valid exporter found for the active collection.")
            return {'CANCELLED'}

        wm = context.window_manager
        exporter = find_exporter(collection, wm.export_format)
        export_path = exporter.export_properties.filepath
        export_dir = os.path.dirname(export_path)
        export_dir = clean_relative_path(os.path.dirname(export_dir))

        if not os.path.exists(export_dir):
            self.report({'WARNING'}, f"Directory does not exist: {export_dir}")
            return {'CANCELLED'}

        bpy.ops.file.external_operation(filepath=export_dir, operation='FOLDER_OPEN')
        self.report({'INFO'}, f"Opened directory: {export_dir}")
        return {'FINISHED'}


classes = (SIMPLEEXPORTER_PT_ExportResultsPanel,
           SIMPLEEXPORTER_PT_FilePathResultsPanel,
           SCENE_OT_SelectAllCollections,
           SCENE_OT_SetExporterPath,
           SCENE_OT_SetExporterPathSelection,
           SCENE_OT_ExportCollection,
           SCENE_OT_ExportCollectionsSelection,
           SCENE_OT_OpenExportDirectory,)


def register():
    bpy.types.WindowManager.export_data_info = bpy.props.StringProperty(default="[]")
    bpy.types.WindowManager.assign_filepath_result_info = bpy.props.StringProperty(default="[]")

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    del bpy.types.WindowManager.export_data_info
    del bpy.types.WindowManager.assign_filepath_result_info

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
