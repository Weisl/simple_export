# needed for adding direct link to settings
import os
import platform
import subprocess
import bpy


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
