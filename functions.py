import os
import platform
import subprocess

import bpy
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


def ensure_export_directory(exporter):
    """
    Ensure the directory for the export path exists, creating it if necessary.
    """
    export_path = exporter.export_properties.filepath
    export_dir = os.path.dirname(export_path)

    if export_dir and not os.path.exists(export_dir):
        os.makedirs(export_dir)
        print(f"Created export directory: {export_dir}")


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
    """
    prefs = bpy.context.preferences.addons[__package__].preferences

    # Temporarily remove the collection offset update handler
    if update_collection_offset in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_collection_offset)

    try:
        # Apply the instance offset if the preference is enabled
        if prefs.use_instance_offset:
            apply_collection_offset(collection)

        set_active_collection(collection.name)
        ensure_export_directory(collection.exporters[0])
        exporter = collection.exporters[0]
        export_path = exporter.export_properties.filepath
        print(f"Preparing to export collection: {collection.name} to {export_path}")

        ensure_export_directory(exporter)
        bpy.ops.collection.exporter_export(index=0)

        print(f"Exported collection '{collection.name}' to '{export_path}'")

        if prefs.use_instance_offset:
            apply_collection_offset(collection, inverse=True)

    finally:
        # Re-enable the collection offset update handler
        if update_collection_offset not in bpy.app.handlers.depsgraph_update_post:
            bpy.app.handlers.depsgraph_update_post.append(update_collection_offset)


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
