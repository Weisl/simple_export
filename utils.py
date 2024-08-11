# needed for adding direct link to settings
import os
import platform
import subprocess
import bpy

from mathutils import Matrix

def apply_location_offset(obj, collection_offset, inverse=False):
    """
    Adjusts the location of an object based on the collection's offset.
    When inverse is False, moves the object so that its distance from the world origin matches its distance from the collection offset.
    When inverse is True, moves the object back to its original position relative to the collection offset.
    """
    if inverse:
        offset_matrix = Matrix.Translation(collection_offset)
    else:
        offset_matrix = Matrix.Translation(-collection_offset)

    # Decompose the matrix_world into translation, rotation, and scale
    loc, rot, scale = obj.matrix_world.decompose()

    # Rebuild the matrix_world with the applied offset
    # We only modify the location component here
    new_loc = offset_matrix @ Matrix.Translation(loc)

    # Construct the final transformation matrix using the unchanged rotation and scale
    obj.matrix_world = new_loc @ rot.to_matrix().to_4x4() @ Matrix.Diagonal(scale).to_4x4()

def apply_collection_offset(collection, inverse=False):
    """
    Applies or removes the collection's instance offset to all objects in the collection,
    moving them relative to the world origin.
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

    Args:
        exporter (bpy.types.PropertyGroup): The exporter containing the export path.
    """
    export_path = exporter.export_properties.filepath
    export_dir = os.path.dirname(export_path)
    if export_dir and not os.path.exists(export_dir):
        os.makedirs(export_dir)


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

    # Optionally apply the instance offset
    if prefs.use_instance_offset:
        apply_collection_offset(collection)

    set_active_collection(collection.name)
    ensure_export_directory(collection.exporters[0])

    # Perform the export
    bpy.ops.collection.exporter_export(index=0)

    # Reset the instance offset after export, if applied
    # if prefs.use_instance_offset:
    #     apply_collection_offset(collection, inverse=True)



def open_directory(export_dir):
    """
    Open the given directory in the file explorer.

    Args:
        export_dir (str): The directory to open.
    """
    if platform.system() == "Windows":
        subprocess.Popen(f'explorer "{export_dir}"')
    elif platform.system() == "Darwin":
        subprocess.Popen(["open", export_dir])
    else:  # Linux and other platforms
        subprocess.Popen(["xdg-open", export_dir])
