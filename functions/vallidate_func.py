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

    Delegates to the structured checks in validation/checks.py so the same
    detection logic backs both these automatic export-time warnings and the
    manual "Validate Selected" popup - only the gating differs: this function
    always runs these checks, while the popup gates them behind the user's
    `prefs.validate_check_*` toggles.
    """
    from ..validation.checks import (
        check_missing_library_reference,
        check_all_objects_hidden_from_render,
        check_no_mesh_objects,
        check_missing_textures,
    )

    issues = []
    for obj in collection.objects:
        issue = check_missing_library_reference(collection, obj)
        if issue:
            issues.append(issue)

    for check in (check_all_objects_hidden_from_render, check_no_mesh_objects):
        issue = check(collection)
        if issue:
            issues.append(issue)

    issue = check_missing_textures(collection, exporter)
    if issue:
        issues.append(issue)

    return [
        f"Object '{issue.object_name}' {issue.message}" if issue.object_name else issue.message
        for issue in issues
    ]


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
