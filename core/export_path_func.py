import os

from ..core.export_formats import ExportFormats
from ..functions.path_utils import ensure_export_folder_exists


def generate_export_path(collection_name, export_format_key, export_dir, search_path, replacement_path):
    """
    Set the export path for a given collection's exporter.

    Args:
        collection_name (str): The name of the collection.
        exporter_dir (str): Path to the export folder.
        search_path (str): The original path to be replaced.
        replacement_path (str): The replacement path to be applied.
        @param export_dir:
        @param replacement_path:
        @param search_path:
        @param collection_name:
        @param export_format_key:
    """

    # Retrieve export format object
    export_format = ExportFormats.get(export_format_key)

    if not export_format:
        raise ValueError(f"Invalid export format: {export_format_key}")

    # Construct export filename
    export_extension = export_format.file_extension
    export_name = f"{collection_name}.{export_extension}"
    export_path = os.path.join(export_dir, export_name)

    # Apply path replacement if needed
    if search_path and replacement_path and search_path in export_path:
        export_path = export_path.replace(search_path, replacement_path)

    return export_path


def assign_exporter_path(exporter, export_path):
    ensure_export_folder_exists(export_path)

    if not exporter:
        msg = "No valid exporter found"
        return False, msg

    if not export_path:
        msg = "Please select a Preset"
        return False, msg

    # Apply the properties to the exporter
    exporter.export_properties.filepath = export_path

    return True, None
