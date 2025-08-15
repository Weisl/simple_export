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


def find_exporter(collection, format_filter=None):
    """
    Find the appropriate exporter for the given collection and format.
    """

    if len(collection.exporters) == 0:
        return None

    # If no export format is specified, return the first exporter
    if format_filter is None:
        return collection.exporters[0]

    # Retrieve export format object
    export_format = ExportFormats.get(format_filter)
    if not export_format:
        raise ValueError(f"Invalid export format: {export_format}")

    # Check collection exporters, return the first matching exporter
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
    export_format = operator.export_format

    scene = context.scene
    set_active_layer_Collection(collection.name)

    export_data = ExportFormats.get(export_format)

    if not export_data:
        operator.report({'ERROR'}, f"Invalid export format: {export_format}")
        return None

    exporters_before = get_all_exporters(collection)

    export_data = ExportFormats.get(export_format)
    operator_name = export_data.op_name

    bpy.ops.collection.exporter_add(name=operator_name)
    exporters_after = get_all_exporters(collection)

    exporter = list(set(exporters_after) - set(exporters_before))[0]

    return exporter


def get_all_children_and_descendants(obj, include_top=False):
    """
    Returns a list of all children and descendants of the given object.
    """
    children = []

    if include_top:
        children.append(obj)

    def recursive_collect(o):
        for child in o.children:
            children.append(child)
            recursive_collect(child)

    recursive_collect(obj)
    return children
