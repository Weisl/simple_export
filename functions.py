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
