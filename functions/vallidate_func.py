import bpy
import os

from .path_utils import ensure_export_folder_exists


def validate_collection(collection_name):
    """Validate the collection and return it if valid."""
    if not collection_name or not bpy.data.collections.get(collection_name):
        return None  # Return None for invalid collections
    return bpy.data.collections.get(collection_name)


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
