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
    Properly handles both relative and absolute paths.
    """

    if not export_path:
        print("ERROR: Export path is empty. Please specify a valid export folder.")
        return False

    # Convert entire export_path to absolute first
    folder_path_absolute = bpy.path.abspath(export_path)
    if not os.path.isabs(folder_path_absolute):
        folder_path_absolute = os.path.abspath(folder_path_absolute)

    # Extract the directory portion and normalize
    export_dir = os.path.dirname(folder_path_absolute)
    export_dir = os.path.normpath(export_dir)

    # Ensure directory is valid
    if not os.path.isabs(export_dir) or export_dir in ["", ".", "\\", "//"]:
        print(f"ERROR: Invalid export directory: {export_dir}")
        return False

    # Ensure directory exists
    if not os.path.exists(export_dir):
        try:
            os.makedirs(export_dir, exist_ok=True)
            print(f"Created export directory: {export_dir}")
        except OSError as e:
            print(f"Failed to create directory: {e}")
            return False

    return True
