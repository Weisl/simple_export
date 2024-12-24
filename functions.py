import platform
import subprocess
from mathutils import Matrix

from .collection_utils import update_collection_offset


def apply_location_offset(obj, collection_offset, inverse=False):
    """
    Adjusts the location of an object based on the collection's offset.
    """
    offset_matrix = Matrix.Translation(-collection_offset if not inverse else collection_offset)

    # Decompose the matrix_world into translation, rotation, and scale
    loc, rot, scale = obj.matrix_world.decompose()

    # Apply the offset to the location
    new_loc = offset_matrix @ Matrix.Translation(loc)

    # Rebuild the matrix_world with the modified location, maintaining rotation and scale
    obj.matrix_world = new_loc @ rot.to_matrix().to_4x4() @ Matrix.Diagonal(scale).to_4x4()


def apply_collection_offset(collection, inverse=False):
    """
    Applies or removes the collection's instance offset to all top-level objects in the collection.
    """
    collection_offset = collection.instance_offset

    for obj in collection.all_objects:
        if obj.parent is None:  # Only apply to top-level objects
            apply_location_offset(obj, collection_offset, inverse)


def get_addon_name():
    """
    Returns the addon name as a string.
    """
    return "Simple Export"


import os
import bpy


def ensure_export_folder_exists(export_path):
    """
    Ensure the directory for the export path exists, creating it if necessary.
    Handles both relative and absolute paths properly.
    """
    export_dir = os.path.dirname(export_path)

    # Convert relative path (//) to absolute path
    if not os.path.isabs(export_dir):
        export_dir = bpy.path.abspath(export_dir)

    # Normalize to handle slashes, backslashes, and .. correctly
    export_dir = os.path.normpath(export_dir)

    # Ensure directory exists
    if export_dir and not os.path.exists(export_dir):
        try:
            os.makedirs(export_dir, exist_ok=True)
            print(f"Created export directory: {export_dir}")
        except OSError as e:
            print(f"Failed to create directory: {e}")
            return False

    return True


def set_active_collection(collection_name):
    """
    Set the given collection as the active collection.

    Args:
        collection_name (str): The name of the collection to set as active.
    """
    layer_collection = bpy.context.view_layer.layer_collection
    for layer in layer_collection.children:
        if layer.name == collection_name:
            bpy.context.view_layer.active_layer_collection = layer
            return


def export_collection(collection, context):
    """
    Handles the export logic for a single collection.

    Args:
        collection (bpy.types.Collection): The collection to export.
        context (bpy.types.Context): The current context.

    Returns:
        dict: A dictionary with 'success' (bool) and 'message' (str) keys.
    """

    prefs = bpy.context.preferences.addons[__package__].preferences
    props = context.scene.simple_export_props
    wm = context.window_manager
    settings_col = wm if wm.overwrite_collection_settings else prefs
    settings_filepath = wm if wm.overwrite_filepath_settings else prefs

    # Temporarily remove the collection offset update handler
    if update_collection_offset in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_collection_offset)

    # Validate exporter availability
    if not collection.exporters or not collection.exporters[0]:
        raise ValueError("No exporter configured for the collection.")

    from .operators import find_exporter
    exporter = find_exporter(collection, props.export_format)
    print(f'Exporter: {exporter}')
    export_path = exporter.export_properties.filepath
    print(f'Exporter Path: {export_path}')

    # Ensure the export directory exists
    ensure_export_folder_exists(export_path)

    # Apply instance offset if the preference is enabled
    if wm.move_to_origin:
        apply_collection_offset(collection)

    # Set the active collection
    set_active_collection(collection.name)

    # Clear Blender's report logs to ensure a clean state
    try:
        # Perform the export operation and check its result
        result = bpy.ops.collection.exporter_export(index=0)
        print(f'Exporter Result: {result}')

        if 'FINISHED' not in result:
            raise RuntimeError(f"Export operator did not finish successfully for '{collection.name}'.")

        # Check Blender's reports for any errors
        report_messages = []
        for report in context.window_manager.reports:
            if report.type == 'ERROR':
                report_messages.append(report.message)

        if report_messages:
            raise RuntimeError(f"Errors during export: {'; '.join(report_messages)}")

        # Additional validations (if necessary) can go here, e.g., reading the file to verify contents.

        print(f"Exported collection '{collection.name}' to '{export_path}'")
        msg = {'success': True, 'message': f"Exported successfully to {export_path}."}

    except Exception as e:
        msg = {'success': False, 'message': f"Unexpected error: {str(e)}"}

    finally:
        # Revert instance offset if applied
        if wm.move_to_origin:
            apply_collection_offset(collection, inverse=True)

        # Re-enable the collection offset update handler
        if update_collection_offset not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(update_collection_offset)

    return msg


def open_directory(export_dir):
    """
    Open the given directory in the file explorer.
    """
    if platform.system() == "Windows":
        subprocess.Popen(f'explorer "{export_dir}"')
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", export_dir])
    else:  # Linux and other platforms
        subprocess.Popen(["xdg-open", export_dir])
