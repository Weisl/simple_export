import bpy
import errno
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

def make_folder_path_absolute(path):
    # Convert entire export_path to absolute first
    folder_path_absolute = bpy.path.abspath(path)
    if not os.path.isabs(folder_path_absolute):
        folder_path_absolute = os.path.abspath(folder_path_absolute)
    return folder_path_absolute

def extract_directory(path):
    # Extract the directory portion and normalize
    path_dir = os.path.dirname(path)
    path_dir = os.path.normpath(path_dir)
    return path_dir

def ensure_export_folder_exists(export_path):
    """
    Ensure the directory for the export path exists, creating it if necessary.
    Properly handles both relative and absolute paths.

    Returns:
        tuple: (success: bool, message: str)
    """

    if not export_path:
        msg = "Export path is empty. Please specify a valid export folder."
        print(f"ERROR: {msg}")
        return False, msg

    export_path = make_folder_path_absolute(export_path)
    export_dir = extract_directory(export_path)

    # Ensure directory is valid
    if not os.path.isabs(export_dir) or export_dir in ["", ".", "\\", "//"]:
        msg = (
            f"Invalid export directory '{export_dir}'. "
            "If using a relative path, make sure the .blend file is saved first."
        )
        print(f"ERROR: {msg}")
        return False, msg

    # Ensure directory exists
    if not os.path.exists(export_dir):
        try:
            os.makedirs(export_dir, exist_ok=True)
            print(f"Created export directory: {export_dir}")
        except OSError as e:
            if e.errno == errno.EACCES:
                msg = f"Permission denied: cannot create export folder '{export_dir}'."
            elif e.errno == errno.ENOENT:
                msg = f"Invalid path: a component of '{export_dir}' does not exist and could not be created."
            else:
                msg = f"Could not create export folder '{export_dir}': {e.strerror}."
            print(f"ERROR: {msg}")
            return False, msg

    return True, ""
