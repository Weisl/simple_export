import bpy
from .collection_layer import set_active_layer_Collection
from ..core.export_formats import ExportFormats


def add_extension(path, export_format_key):
    export_format = ExportFormats.get(export_format_key)

    if not export_format:
        raise ValueError(f"Invalid export format: {export_format_key}")

    file_extension = f".{export_format.file_extension}"

    # Check if the filename already has the extension
    if not path.lower().endswith(file_extension.lower()):
        path += file_extension

    return path


def find_exporter(collection, export_format_key):
    """
    Find the appropriate exporter for the given collection and format.
    """
    # Retrieve export format object
    export_format = ExportFormats.get(export_format_key)

    if not export_format:
        raise ValueError(f"Invalid export format: {export_format_key}")

    # Check collection exporters
    for exporter in collection.exporters:
        if str(type(exporter.export_properties)) == export_format.op_type:
            return exporter

    return None  # Return None if no valid exporter is found


def get_exporter_id(self, collection, exporter):
    """Get the exporter ID within the collection."""
    for idx, exp in enumerate(collection.exporters):
        if exp == exporter:
            return idx
    raise ValueError(f"{exporter.name} not found in the exporters of collection '{self.collection_name}'.")


def get_all_exporters(collection):
    return list(collection.exporters)


def assign_collection_exporter(operator, context, collection):
    if collection is None:
        operator.report({'ERROR'}, "Collection is None in assign_collection_exporter.")
        return None

    scene = context.scene
    set_active_layer_Collection(collection.name)

    export_data = ExportFormats.get(scene.export_format)

    if not export_data:
        operator.report({'ERROR'}, f"Invalid export format: {scene.export_format}")
        return None

    exporters_before = get_all_exporters(collection)

    export_data = ExportFormats.get(scene.export_format)
    operator_name = export_data.op_name

    bpy.ops.collection.exporter_add(name=operator_name)
    exporters_after = get_all_exporters(collection)

    exporter = list(set(exporters_after) - set(exporters_before))[0]
