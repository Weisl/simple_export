import bpy
import os

from .path_utils import ensure_export_folder_exists


def validate_collection(collection_name):
    """Validate the collection and return it if valid."""
    if not collection_name or not bpy.data.collections.get(collection_name):
        return None  # Return None for invalid collections
    return bpy.data.collections.get(collection_name)


def _get_missing_textures(collection):
    """Return names of missing (non-packed, file-sourced) image textures used by mesh objects."""
    missing = []
    seen = set()
    for obj in collection.objects:
        if obj.type != 'MESH':
            continue
        for slot in obj.material_slots:
            mat = slot.material
            if not mat or not mat.use_nodes:
                continue
            for node in mat.node_tree.nodes:
                if node.type != 'TEX_IMAGE' or not node.image:
                    continue
                img = node.image
                if img.name in seen:
                    continue
                seen.add(img.name)
                if img.packed_file or img.source != 'FILE' or not img.filepath:
                    continue
                if not os.path.exists(bpy.path.abspath(img.filepath)):
                    missing.append(img.name)
    return missing


def check_collection_warnings(collection, exporter):
    """Return a list of non-blocking warning strings for this collection.

    These do not block the export but are surfaced in the results popup.
    """
    warnings = []

    # Missing linked library references
    for obj in collection.objects:
        if obj.library:
            lib_path = bpy.path.abspath(obj.library.filepath)
            if not os.path.exists(lib_path):
                warnings.append(
                    f"Object '{obj.name}' references missing library: '{obj.library.filepath}'."
                )

    # All objects excluded from render
    if collection.objects and not any(not obj.hide_render for obj in collection.objects):
        warnings.append("All objects are excluded from render.")

    # No mesh objects in collection
    if collection.objects and not any(obj.type == 'MESH' for obj in collection.objects):
        types = sorted({obj.type for obj in collection.objects})
        warnings.append(f"No mesh objects (types present: {', '.join(types)}).")

    # Missing textures — only relevant for GLTF and USD which embed/reference them
    from ..core.export_formats import ExportFormats
    op_type = str(type(exporter.export_properties))
    format_key = ExportFormats.get_key_from_op_type(op_type)
    if format_key in ('GLTF', 'USD'):
        missing = _get_missing_textures(collection)
        if missing:
            preview = ', '.join(f"'{n}'" for n in missing[:3])
            extra = f" (+{len(missing) - 3} more)" if len(missing) > 3 else ""
            warnings.append(f"Missing textures: {preview}{extra}.")

    return warnings


def pre_export_checks(export_path):
    """Perform pre-export checks and return file existence and timestamp."""

    file_exists = os.path.exists(export_path)
    file_timestamp = os.path.getmtime(export_path) if file_exists else None

    ensure_export_folder_exists(export_path)
    return file_exists, file_timestamp


def post_export_checks(export_path, file_exists_before, file_timestamp_before):
    """Validate the exported file."""
    if not export_path:
        return False, "No export path specified."
    from .path_utils import make_folder_path_absolute
    export_path = make_folder_path_absolute(export_path)
    # export_dir = extract_directory(export_path)

    if not os.path.exists(export_path):
        export_dir = os.path.dirname(export_path)
        if not os.path.isdir(export_dir):
            return False, f"Export failed: the output folder does not exist: '{export_dir}'."
        if not os.access(export_dir, os.W_OK):
            return False, f"Export failed: no write permission for '{export_dir}'."
        return False, "Export failed: the file was not created. Check the exporter settings or the system console for details."
    if not os.access(export_path, os.W_OK):
        return False, f"Exported file is read-only: '{export_path}'."
    return True, "Export successful."
