import bpy
import os

from ..core.export_formats import ExportFormats
from ..functions.path_utils import ensure_export_folder_exists


def generate_export_path(base_name, export_format_key, export_dir, is_relative_path=False):
    """
    Generate and set the correct export path based on the selected filepath mode.

    Args:
        collection_name (str): The name of the collection.
        export_format_key (str): Export format key.
        export_dir (str): Path to the export folder.
        folder_path_search (str): The original path to be replaced.
        folder_path_replace (str): The replacement path to be applied.
        is_relative_path (bool): Whether the path is set to relative.

    Returns:
        str: The computed export path.
    """

    # Retrieve export format object
    export_format = ExportFormats.get(export_format_key)
    if not export_format:
        raise ValueError(f"Invalid export format: {export_format_key}")

    # Construct export filename
    export_extension = export_format.file_extension
    export_name = f"{base_name}.{export_extension}"

    # Resolve relative paths
    if is_relative_path:
        blend_dir = bpy.path.abspath("//")  # Get the blend file's directory
        export_dir = os.path.join(blend_dir, export_dir) if not os.path.isabs(export_dir) else export_dir

    # Ensure directory exists
    ensure_export_folder_exists(export_dir)

    # Final export path
    export_path = os.path.join(export_dir, export_name)

    return bpy.path.relpath(export_path) if is_relative_path else export_path


def assign_exporter_ops_path(exporter, export_path, is_relative_path):
    """
    Assigns the generated export path to the exporter while ensuring the folder exists.

    Args:
        exporter (object): The export operator object.
        export_path (str): The computed export file path.
        is_relative_path (bool): Whether to keep the path relative to the .blend file.

    Returns:
        tuple: (bool, str) -> (Success, Message)
    """

    if not exporter:
        return False, "No valid exporter found"

    if not export_path:
        return False, "Please select a Preset"

    # Convert relative path to absolute only for directory creation
    folder_path_absolute = bpy.path.abspath(export_path)  # Convert to absolute
    export_dir = os.path.dirname(folder_path_absolute)  # Extract folder path

    # Validate that the export directory is a valid absolute path
    if not os.path.isabs(export_dir) or export_dir in ["", ".", "\\", "//"]:
        return False, f"Invalid export directory: {export_dir}"

    # Ensure the export folder exists using only absolute paths
    ensure_export_folder_exists(export_dir)

    # Assign a relative path if the mode is RELATIVE, otherwise use absolute
    final_export_path = export_path if is_relative_path else folder_path_absolute

    # Assign the correct path format to the exporter
    exporter.export_properties.filepath = final_export_path

    return True, None


def get_export_path(settings_filepath, use_defaults=False):
    """
    Determines the correct export directory based on the user's settings.

    If use_defaults is True, it will return sensible defaults instead of raising errors.

    :param settings_filepath: The file path settings from scene or addon preferences.
    :param use_defaults: If True, uses fallback values instead of raising errors.
    :return: Tuple (export_dir: str, is_relative_path: bool)
    """
    export_dir = None
    is_relative_path = False

    if settings_filepath.export_folder_mode == 'ABSOLUTE':
        if not settings_filepath.folder_path_absolute:
            if use_defaults:
                export_dir = "./"
                is_relative_path = True
            else:
                raise ValueError("ERROR: Please specify a Custom Export Folder!")
        else:
            export_dir = settings_filepath.folder_path_absolute
            is_relative_path = False

    elif settings_filepath.export_folder_mode == 'RELATIVE':
        if not settings_filepath.folder_path_relative:
            if use_defaults:
                export_dir = "//."
                is_relative_path = True
            else:
                raise ValueError("ERROR: Please specify a relative Export Folder Location.")
        else:
            export_dir = settings_filepath.folder_path_relative
            is_relative_path = True

    elif settings_filepath.export_folder_mode == 'MIRROR':
        if not bpy.data.filepath:  # is file saved
            if use_defaults:
                export_dir = "./"
                is_relative_path = True
            else:
                raise ValueError("ERROR: Please save the Blend file before calling this operator.")
        else:
            export_dir = os.path.dirname(bpy.data.filepath)
            is_relative_path = False

            # Apply mirror replacement if needed
            if settings_filepath.folder_path_search and settings_filepath.folder_path_replace and settings_filepath.folder_path_search in export_dir:
                export_dir = export_dir.replace(settings_filepath.folder_path_search,
                                                settings_filepath.folder_path_replace)

    else:
        if use_defaults:
            export_dir = "./"
            is_relative_path = True
        else:
            raise ValueError(f"Unknown export folder mode: {settings_filepath.export_folder_mode}")

    return export_dir, is_relative_path


def assign_export_path_to_exporter(collection, exporter, scene, settings_filepath, settings_filename,
                                   use_defaults=False):
    """
    Assigns an export path to the given exporter based on the configured file path settings.

    :param collection: The collection being exported.
    :param exporter: The exporter assigned to the collection.
    :param scene: The current scene context.
    :param settings_filepath: Filepath settings from either scene or addon preferences.
    :param settings_filename: Object containing filename customization settings.
    :param use_defaults: If True, uses default settings instead of raising errors when paths are missing.

    :return: Tuple (success: bool, export_path: str, message: str)
    """

    try:
        # Get the export directory and relative mode, handling errors based on use_defaults
        export_dir, is_relative_path = get_export_path(settings_filepath, use_defaults)
        # print(f'DEBUG: export_dir: {export_dir}, is_relative_path: {is_relative_path}')


        from ..functions.create_collection_func import generate_base_name

        base_name = generate_base_name(
            collection.name,
            settings_filename.filename_prefix,
            settings_filename.filename_suffix,
            settings_filename.filename_blend_prefix
        )

        # Generate final export path
        export_path = generate_export_path(
            base_name, scene.export_format, export_dir, is_relative_path=is_relative_path)
        # print(f'DEBUG: export_path: {export_path}')


        collection["prev_name"] = collection.name

        # Assign path to exporter
        success, msg = assign_exporter_ops_path(exporter, export_path, settings_filepath.export_folder_mode)
        return success, export_path, msg

    except Exception as e:
        return False, '', str(e)
