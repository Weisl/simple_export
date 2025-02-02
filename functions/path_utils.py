import bpy
import os


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


def ensure_export_folder_exists(export_path):
    """
    Ensure the directory for the export path exists, creating it if necessary.
    Handles both relative and absolute paths properly.
    """
    export_dir = os.path.dirname(export_path)

    # Convert relative path (//) to absolute path
    if not os.path.isabs(export_dir):
        export_dir = bpy.path.abspath(export_dir)

    # Normalize to handle slashes, backslashes, and . correctly
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
