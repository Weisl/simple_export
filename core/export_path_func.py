import os
import warnings

import bpy

from ..core.export_formats import ExportFormats
from ..functions.path_utils import ensure_export_folder_exists


def assign_exporter_path(properties, collection_name, exporter):
    export_folder, is_relative_path = get_export_folder_path(properties.export_folder_mode,
                                                             properties.folder_path_absolute,
                                                             properties.folder_path_relative,
                                                             properties.folder_path_search,
                                                             properties.folder_path_replace)

    filename = generate_base_name(collection_name, properties.filename_prefix, properties.filename_suffix,
                                  properties.filename_blend_prefix, properties.filename_separator)

    export_path = generate_export_path(export_folder, filename, properties.export_format,
                                       is_relative_path=is_relative_path)

    if export_path:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*does not support blend relative.*", category=RuntimeWarning)
            exporter.export_properties.filepath = export_path


def generate_export_path(export_dir, base_name, export_format_key, is_relative_path=False):
    """
    Generate and set the correct export path based on the selected filepath mode.

    Args:
        export_format_key (str): Export format key.
        export_dir (str): Path to the export folder.
        is_relative_path (bool): Whether the path is set to relative.

    Returns:
        str: The computed export path.
    """

    # Retrieve export format object
    export_format = ExportFormats.get(export_format_key)
    if not export_format:
        raise ValueError(f"Invalid export format: {export_format_key}")

    if export_dir == None:
        export_dir = ""

    # Construct export filename
    export_extension = export_format.file_extension
    export_name = f"{base_name}.{export_extension}"

    # Resolve relative paths
    if is_relative_path:
        if not bpy.data.filepath:
            # Blend file not saved — store the raw Blender-relative path as-is.
            # Resolution to absolute happens at export time once the file is saved.
            raw_dir = export_dir if export_dir.startswith("//") else f"//{export_dir}"
            return raw_dir.rstrip("/") + "/" + export_name

        blend_dir = bpy.path.abspath("//")  # Get the blend file's directory
        # Strip Blender's "//" relative-path prefix before using os.path operations.
        # os.path.isabs("//foo") returns True on POSIX, which would bypass the
        # join with blend_dir and leave the raw "//foo" as the export directory.
        clean_dir = export_dir[2:] if export_dir.startswith("//") else export_dir
        export_dir = os.path.join(blend_dir, clean_dir) if not os.path.isabs(clean_dir) else clean_dir

    # Ensure directory exists
    ensure_export_folder_exists(export_dir)

    # Final export path
    export_path = os.path.join(export_dir, export_name)

    return bpy.path.relpath(export_path) if is_relative_path else export_path


def assign_collection_exporter_path(exporter, export_path, is_relative_path):
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
        return False, "Export path is empty. Please specify a valid export folder."

    # Raw Blender-relative path (starts with "//") without a saved blend file:
    # store it as-is without trying to resolve or create folders now.
    if export_path.startswith("//") and not bpy.data.filepath:
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message=".*does not support blend relative.*", category=RuntimeWarning)
            exporter.export_properties.filepath = export_path
        return True, None

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
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*does not support blend relative.*", category=RuntimeWarning)
        exporter.export_properties.filepath = final_export_path

    return True, None


def get_export_folder_path(export_folder_mode, folder_path_absolute, folder_path_relative, folder_path_search,
                           folder_path_replace, use_defaults=False):
    """
    Determines the correct export directory based on the user's settings.

    If use_defaults is True, it will return sensible defaults instead of raising errors.

    :param export_folder_mode: The export folder mode.
    :param folder_path_absolute: The absolute folder path.
    :param folder_path_relative: The relative folder path.
    :param folder_path_search: The search folder path.
    :param folder_path_replace: The replace folder path.
    :param use_defaults: If True, uses fallback values instead of raising errors.
    :return: Tuple (export_dir: str, is_relative_path: bool)
    """
    export_dir = None
    is_relative_path = False

    if export_folder_mode == 'ABSOLUTE':
        if not folder_path_absolute:
            if use_defaults:
                export_dir = "./"
                is_relative_path = True
            # else:
            #     raise ValueError("ERROR: Please specify a Custom Export Folder!")
        else:
            export_dir = folder_path_absolute
            is_relative_path = False

    elif export_folder_mode == 'RELATIVE':
        if not folder_path_relative:
            if use_defaults:
                export_dir = "//."
                is_relative_path = True
            # else:
            #     raise ValueError("ERROR: Please specify a relative Export Folder Location.")
        else:
            export_dir = folder_path_relative
            is_relative_path = True

    elif export_folder_mode == 'MIRROR':
        if not bpy.data.filepath:  # is file saved
            if use_defaults:
                export_dir = "./"
                is_relative_path = True
            # else:
            #     raise ValueError("ERROR: Please save the Blend file before calling this operator.")
        else:
            export_dir = os.path.dirname(bpy.data.filepath)
            is_relative_path = False

            # Apply mirror replacement if needed
            if folder_path_search and folder_path_replace and folder_path_search in export_dir:
                export_dir = export_dir.replace(folder_path_search,
                                                folder_path_replace)

    else:
        if use_defaults:
            export_dir = "./"
            is_relative_path = True
        else:
            raise ValueError(f"Unknown export folder mode: {export_folder_mode}")

    return export_dir, is_relative_path


def generate_base_name(entity_name, prefix='', suffix='', use_file_name=False, separator='_'):
    collection_name = entity_name

    if prefix and not collection_name.startswith(prefix):
        sep = "" if separator and (prefix.endswith(separator) or collection_name.startswith(separator)) else separator
        collection_name = prefix + sep + collection_name

    if suffix and not collection_name.endswith(suffix):
        sep = "" if separator and (suffix.startswith(separator) or collection_name.endswith(separator)) else separator
        collection_name = collection_name + sep + suffix

    if use_file_name:
        file_name_prefix = os.path.splitext(os.path.basename(bpy.data.filepath))[0] or "UNSAVED"
        if not collection_name.startswith(file_name_prefix):
            sep = "" if separator and (file_name_prefix.endswith(separator) or collection_name.startswith(separator)) else separator
            collection_name = file_name_prefix + sep + collection_name

    return collection_name
