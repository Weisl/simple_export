import bpy
import os

from ..core.export_formats import ExportFormats
from ..functions.path_utils import ensure_export_folder_exists


def generate_export_path(base_name, export_format_key, export_dir, mirror_search_path, mirror_replacement_path,
                         relative_mode):
    """
    Generate and set the correct export path based on the selected filepath mode.

    Args:
        collection_name (str): The name of the collection.
        export_format_key (str): Export format key.
        export_dir (str): Path to the export folder.
        mirror_search_path (str): The original path to be replaced.
        mirror_replacement_path (str): The replacement path to be applied.
        relative_mode (bool): Whether the path is set to relative.

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
    if relative_mode:
        blend_dir = bpy.path.abspath("//")  # Get the blend file's directory
        export_dir = os.path.join(blend_dir, export_dir) if not os.path.isabs(export_dir) else export_dir

    # Apply mirror replacement if needed
    if mirror_search_path and mirror_replacement_path and mirror_search_path in export_dir:
        export_dir = export_dir.replace(mirror_search_path, mirror_replacement_path)

    # Ensure directory exists
    ensure_export_folder_exists(export_dir)

    # Final export path
    export_path = os.path.join(export_dir, export_name)

    return bpy.path.relpath(export_path) if relative_mode else export_path


def assign_exporter_path(exporter, export_path, relative_mode):
    """
    Assigns the generated export path to the exporter while ensuring the folder exists.

    Args:
        exporter (object): The export operator object.
        export_path (str): The computed export file path.
        relative_mode (bool): Whether to keep the path relative to the .blend file.

    Returns:
        tuple: (bool, str) -> (Success, Message)
    """

    if not exporter:
        return False, "No valid exporter found"

    if not export_path:
        return False, "Please select a Preset"

    # Convert relative path to absolute only for directory creation
    absolute_export_path = bpy.path.abspath(export_path)  # Convert to absolute
    export_dir = os.path.dirname(absolute_export_path)  # Extract folder path

    # Validate that the export directory is a valid absolute path
    if not os.path.isabs(export_dir) or export_dir in ["", ".", "\\", "//"]:
        return False, f"Invalid export directory: {export_dir}"

    # Ensure the export folder exists using only absolute paths
    ensure_export_folder_exists(export_dir)

    # Assign a relative path if the mode is RELATIVE, otherwise use absolute
    final_export_path = export_path if relative_mode else absolute_export_path

    # Assign the correct path format to the exporter
    exporter.export_properties.filepath = final_export_path

    return True, None


def assign_export_path_to_exporter(collection, exporter, scene, settings_filepath, settings_filename):
    """
    Assigns an export path to the given exporter based on the configured file path settings.

    :param collection: The collection being exported.
    :param exporter: The exporter assigned to the collection.
    :param scene: The current scene context.
    :param settings_filepath: Filepath settings from either scene or addon preferences.
    :return: Tuple (success: bool, export_path: str, message: str)
    """
    try:
        if settings_filepath.export_folder_mode == 'ABSOLUTE':
            if not settings_filepath.absolute_export_path:
                raise ValueError("ERROR: Please specify a Custom Export Folder!")
            export_dir = settings_filepath.absolute_export_path
            relative_mode = False

        elif settings_filepath.export_folder_mode == 'RELATIVE':
            if not bpy.data.filepath:
                raise ValueError("Save the Blend file before calling this operator.")
            export_dir = settings_filepath.relative_export_path
            relative_mode = True

        elif settings_filepath.export_folder_mode == 'MIRROR':
            if not bpy.data.filepath:
                raise ValueError("Save the Blend file before calling this operator.")
            export_dir = os.path.dirname(bpy.data.filepath)
            relative_mode = False  # Mirrored paths are not inherently relative

        else:
            raise ValueError(f"Unknown export folder mode: {settings_filepath.export_folder_mode}")

        from ..functions.create_collection_func import generate_base_name

        base_name = generate_base_name(collection.name, settings_filename.filename_custom_prefix, settings_filename.filename_custom_suffix,
                                       settings_filename.filename_file_name_prefix)

        # Generate final export path
        export_path = generate_export_path(
            base_name, scene.export_format, export_dir,
            settings_filepath.mirror_search_path, settings_filepath.mirror_replacement_path, relative_mode
        )

        collection["prev_name"] = collection.name

        # Assign path to exporter
        success, msg = assign_exporter_path(exporter, export_path, settings_filepath.export_folder_mode)
        return success, export_path, msg

    except Exception as e:
        return False, '', str(e)
