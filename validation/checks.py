import os
import re
from dataclasses import dataclass

import bmesh
import bpy


@dataclass(frozen=True)
class ValidationIssue:
    check_id: str
    collection_name: str
    object_name: str  # '' for a collection-level issue with no single offending object
    severity: str      # 'ERROR' | 'WARNING' | 'INFO'
    message: str        # does not repeat "Object 'X'" / the collection name - the UI supplies that via grouping


_NUMERIC_SUFFIX_RE = re.compile(r'\.\d{3}$')

# Letters, digits, underscore, hyphen and dot are considered safe - dot is
# allowed here since the numeric ".001"-style duplicate suffix is already its
# own dedicated check (check_numeric_suffix_name); flagging it again here as
# an "invalid character" would just be a redundant second warning for the
# same underlying dot.
_INVALID_NAME_CHARS_RE = re.compile(r'[^A-Za-z0-9_\-.]')


def _describe_invalid_characters(name):
    invalid = sorted(set(_INVALID_NAME_CHARS_RE.findall(name)))
    if not invalid:
        return None
    chars = ', '.join("' ' (space)" if c == ' ' else f"'{c}'" for c in invalid)
    return f"name contains invalid character(s): {chars} - use only letters, numbers, underscores, hyphens and dots"


def _issue(check_id, collection, obj, severity, message):
    return ValidationIssue(
        check_id=check_id,
        collection_name=collection.name,
        object_name=obj.name if obj is not None else '',
        severity=severity,
        message=message,
    )


# ---------------------------------------------------------------------------
# Object-level checks
# ---------------------------------------------------------------------------

def check_missing_material_slot(collection, obj):
    """Flag a mesh object with a face resolving to no material (renders as the
    engine's default/pink material)."""
    mesh = obj.data
    materials = mesh.materials
    for p in mesh.polygons:
        if not materials or p.material_index >= len(materials) or materials[p.material_index] is None:
            return _issue('missing_material_slot', collection, obj, 'ERROR',
                          "has one or more faces with no material assigned")
    return None


def check_negative_scale(collection, obj):
    """Flag un-applied negative scale, which flips face winding on export."""
    if all(s >= 0 for s in obj.scale):
        return None
    scale = tuple(round(s, 3) for s in obj.scale)
    return _issue('negative_scale', collection, obj, 'ERROR',
                  f"has negative scale {scale} - apply scale before export")


def check_missing_library_reference(collection, obj):
    """Flag a linked object whose source .blend no longer exists on disk."""
    if not obj.library:
        return None
    lib_path = bpy.path.abspath(obj.library.filepath)
    if os.path.exists(lib_path):
        return None
    return _issue('missing_library_reference', collection, obj, 'ERROR',
                  f"references missing library: '{obj.library.filepath}'.")


def check_missing_uv_map(collection, obj):
    """Flag a mesh with no UV layer - breaks texturing/baking in most engines."""
    if len(obj.data.uv_layers) > 0:
        return None
    return _issue('missing_uv_map', collection, obj, 'WARNING', "has no UV map")


def check_too_many_uv_maps(collection, obj, max_uv_maps):
    """Flag a mesh with more UV maps than expected. Extra UV channels (e.g. a
    second baked-lightmap UV) are often intentional, so this is informational
    only."""
    count = len(obj.data.uv_layers)
    if count <= max_uv_maps:
        return None
    return _issue('too_many_uv_maps', collection, obj, 'INFO',
                  f"has {count} UV maps (expected at most {max_uv_maps})")


def check_uv_out_of_bounds(collection, obj):
    """Flag UVs outside the 0-1 range. Often intentional (tiling/trim-sheets),
    so this is informational only."""
    uv_layers = obj.data.uv_layers
    if not uv_layers:
        return None
    uv_layer = uv_layers.active or uv_layers[0]
    for loop_uv in uv_layer.data:
        u, v = loop_uv.uv
        if u < 0.0 or u > 1.0 or v < 0.0 or v > 1.0:
            return _issue('uv_out_of_bounds', collection, obj, 'INFO', "has UVs outside the 0-1 range")
    return None


def check_ngons_present(collection, obj, depsgraph):
    """Flag n-gon faces (5+ sides), which triangulate unpredictably on export."""
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = obj_eval.to_mesh()
    try:
        if any(len(p.vertices) > 4 for p in mesh.polygons):
            return _issue('ngons_present', collection, obj, 'WARNING', "has n-gon faces (5+ sides)")
        return None
    finally:
        obj_eval.to_mesh_clear()


def check_non_manifold_geometry(collection, obj, depsgraph):
    """Flag edges that aren't shared by exactly two faces."""
    obj_eval = obj.evaluated_get(depsgraph)
    mesh = obj_eval.to_mesh()
    try:
        bm = bmesh.new()
        bm.from_mesh(mesh)
        non_manifold_count = sum(1 for e in bm.edges if not e.is_manifold)
        bm.free()
    finally:
        obj_eval.to_mesh_clear()

    if non_manifold_count == 0:
        return None
    return _issue('non_manifold_geometry', collection, obj, 'WARNING',
                  f"has {non_manifold_count} non-manifold edge(s)")


def check_loose_geometry(collection, obj):
    """Flag vertices/edges not part of any face - near-always unintended cruft."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    loose_verts = sum(1 for v in bm.verts if not v.link_faces)
    loose_edges = sum(1 for e in bm.edges if not e.link_faces)
    bm.free()

    if loose_verts == 0 and loose_edges == 0:
        return None
    parts = []
    if loose_verts:
        parts.append(f"{loose_verts} loose vertex/vertices")
    if loose_edges:
        parts.append(f"{loose_edges} loose edge(s)")
    return _issue('loose_geometry', collection, obj, 'WARNING', f"has {' and '.join(parts)}")


def check_numeric_suffix_name(collection, obj):
    """Flag a Blender-generated '.001'-style duplicate suffix, which importers
    like Unity/Unreal's FBX pipeline often strip or rename, risking silent
    collisions between assets."""
    if not _NUMERIC_SUFFIX_RE.search(obj.name):
        return None
    return _issue('numeric_suffix_name', collection, obj, 'WARNING',
                  "has a numeric duplicate suffix in its name - consider renaming before export")


def check_invalid_characters_in_name(collection, obj):
    """Flag an object name containing spaces or special characters, which
    many target engines (Unity/Unreal) don't allow and will silently
    sanitize or reject on import."""
    message = _describe_invalid_characters(obj.name)
    if message is None:
        return None
    return _issue('invalid_characters_in_name', collection, obj, 'WARNING', message)


def check_unused_material_slot(collection, obj):
    """Flag a material slot no face references - harmless, but usually leftover data."""
    mesh = obj.data
    if not mesh.materials:
        return None
    used_indices = {p.material_index for p in mesh.polygons}
    unused = [i for i, mat in enumerate(mesh.materials) if mat is not None and i not in used_indices]
    if not unused:
        return None
    names = ', '.join(f"'{mesh.materials[i].name}'" for i in unused)
    return _issue('unused_material_slot', collection, obj, 'INFO', f"has unused material slot(s): {names}")


def check_non_uniform_scale(collection, obj):
    """Flag non-uniform scale. A documented gotcha on some engines, but often
    harmless since exporters bake the world transform - informational only."""
    sx, sy, sz = obj.scale
    if abs(sx - sy) < 1e-5 and abs(sy - sz) < 1e-5:
        return None
    return _issue('non_uniform_scale', collection, obj, 'INFO',
                  f"has non-uniform scale ({sx:.3f}, {sy:.3f}, {sz:.3f})")


def check_uniform_scale_not_applied(collection, obj):
    """Flag uniform (but != 1) scale. Some pipelines want everything pre-applied;
    usually harmless otherwise - informational only."""
    sx, sy, sz = obj.scale
    if abs(sx - sy) > 1e-5 or abs(sy - sz) > 1e-5:
        return None  # non-uniform scale is check_non_uniform_scale's concern
    if abs(sx - 1.0) < 1e-5:
        return None
    return _issue('uniform_scale_not_applied', collection, obj, 'INFO', f"scale ({sx:.3f}) not applied")


# ---------------------------------------------------------------------------
# Collection-level checks
# ---------------------------------------------------------------------------

def check_all_objects_hidden_from_render(collection):
    """Flag a collection where every object is excluded from render - the
    export would produce nothing visible."""
    if collection.objects and not any(not obj.hide_render for obj in collection.objects):
        return _issue('all_objects_hidden_from_render', collection, None, 'ERROR',
                      "All objects are excluded from render.")
    return None


def check_no_mesh_objects(collection):
    """Flag an export collection with no MESH objects - usually a mistake."""
    if collection.objects and not any(obj.type == 'MESH' for obj in collection.objects):
        types = sorted({obj.type for obj in collection.objects})
        return _issue('no_mesh_objects', collection, None, 'ERROR',
                      f"No mesh objects (types present: {', '.join(types)}).")
    return None


def check_collection_name_invalid_characters(collection):
    """Flag an export collection name containing spaces or special
    characters - the collection name is typically used as the exported
    filename base, and many target engines don't allow these either."""
    message = _describe_invalid_characters(collection.name)
    if message is None:
        return None
    return _issue('invalid_characters_in_name', collection, None, 'WARNING', message)


def check_missing_textures(collection, exporter):
    """Flag missing (non-packed, file-sourced) image textures - only relevant
    for GLTF/USD, which embed/reference them."""
    from ..core.export_formats import ExportFormats
    from ..functions.vallidate_func import _get_missing_textures

    op_type = str(type(exporter.export_properties))
    format_key = ExportFormats.get_key_from_op_type(op_type)
    if format_key not in ('GLTF', 'USD'):
        return None

    missing = _get_missing_textures(collection)
    if not missing:
        return None
    preview = ', '.join(f"'{n}'" for n in missing[:3])
    extra = f" (+{len(missing) - 3} more)" if len(missing) > 3 else ""
    return _issue('missing_textures', collection, None, 'WARNING', f"Missing textures: {preview}{extra}.")


def check_triangle_count(collection, max_triangles, depsgraph):
    """Flag a collection whose combined evaluated triangle count exceeds the
    budget. A tris budget is naturally per export-collection, not per object."""
    total_tris = 0
    for obj in collection.objects:
        if obj.type != 'MESH':
            continue
        obj_eval = obj.evaluated_get(depsgraph)
        mesh = obj_eval.to_mesh()
        try:
            total_tris += sum(len(p.vertices) - 2 for p in mesh.polygons)
        finally:
            obj_eval.to_mesh_clear()

    if total_tris <= max_triangles:
        return None
    return _issue('triangle_count', collection, None, 'WARNING',
                  f"{total_tris} triangles across the collection (limit {max_triangles})")


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------

def collect_validation_issues(collections, prefs, depsgraph, progress_callback=None):
    """Run every enabled check over `collections` and return the list of issues found.

    A collection raising on its checks (e.g. malformed data) is reported as its
    own issue rather than aborting the whole scan, so one bad collection can't
    hide results for everything else. `progress_callback`, if given, is called
    with (done_count, total_count) after each collection is processed - used by
    the operator to drive a wm.progress_begin/update/end bar on large scenes.
    """
    issues = []
    collections = list(collections)

    for index, collection in enumerate(collections):
        try:
            issues.extend(_collect_collection_issues(collection, prefs, depsgraph))
        except Exception as exc:
            issues.append(ValidationIssue(
                check_id='internal_error',
                collection_name=collection.name,
                object_name='',
                severity='ERROR',
                message=f"validation check failed on this collection: {exc}",
            ))
        finally:
            if progress_callback is not None:
                progress_callback(index + 1, len(collections))

    return issues


def _collect_collection_issues(collection, prefs, depsgraph):
    """Run collection-level checks, then every object's checks (each object
    wrapped in its own try/except so a raise there can't hide the rest of this
    collection's - or any other collection's - results)."""
    issues = []

    if prefs.validate_check_all_objects_hidden_from_render:
        issue = check_all_objects_hidden_from_render(collection)
        if issue:
            issues.append(issue)

    if prefs.validate_check_no_mesh_objects:
        issue = check_no_mesh_objects(collection)
        if issue:
            issues.append(issue)

    if prefs.validate_check_invalid_characters_in_name:
        issue = check_collection_name_invalid_characters(collection)
        if issue:
            issues.append(issue)

    if prefs.validate_check_triangle_count:
        issue = check_triangle_count(collection, prefs.validation_max_triangle_count, depsgraph)
        if issue:
            issues.append(issue)

    if prefs.validate_check_missing_textures:
        from ..functions.exporter_funcs import find_exporter
        exporter = find_exporter(collection)
        if exporter is not None:
            issue = check_missing_textures(collection, exporter)
            if issue:
                issues.append(issue)

    for obj in collection.objects:
        try:
            issues.extend(_collect_object_issues(collection, obj, prefs, depsgraph))
        except Exception as exc:
            issues.append(ValidationIssue(
                check_id='internal_error',
                collection_name=collection.name,
                object_name=obj.name,
                severity='ERROR',
                message=f"validation check failed on this object: {exc}",
            ))

    return issues


def _collect_object_issues(collection, obj, prefs, depsgraph):
    """Run every enabled check against a single object."""
    issues = []

    if prefs.validate_check_missing_library_reference:
        issue = check_missing_library_reference(collection, obj)
        if issue:
            issues.append(issue)

    if prefs.validate_check_numeric_suffix_name:
        issue = check_numeric_suffix_name(collection, obj)
        if issue:
            issues.append(issue)

    if prefs.validate_check_invalid_characters_in_name:
        issue = check_invalid_characters_in_name(collection, obj)
        if issue:
            issues.append(issue)

    if obj.type != 'MESH':
        return issues

    if prefs.validate_check_negative_scale:
        issue = check_negative_scale(collection, obj)
        if issue:
            issues.append(issue)

    if prefs.validate_check_non_uniform_scale:
        issue = check_non_uniform_scale(collection, obj)
        if issue:
            issues.append(issue)

    if prefs.validate_check_uniform_scale_not_applied:
        issue = check_uniform_scale_not_applied(collection, obj)
        if issue:
            issues.append(issue)

    if prefs.validate_check_missing_uv_map:
        issue = check_missing_uv_map(collection, obj)
        if issue:
            issues.append(issue)

    if prefs.validate_check_too_many_uv_maps:
        issue = check_too_many_uv_maps(collection, obj, prefs.validation_max_uv_maps)
        if issue:
            issues.append(issue)

    if prefs.validate_check_uv_out_of_bounds:
        issue = check_uv_out_of_bounds(collection, obj)
        if issue:
            issues.append(issue)

    if prefs.validate_check_ngons_present:
        issue = check_ngons_present(collection, obj, depsgraph)
        if issue:
            issues.append(issue)

    if prefs.validate_check_non_manifold_geometry:
        issue = check_non_manifold_geometry(collection, obj, depsgraph)
        if issue:
            issues.append(issue)

    if prefs.validate_check_loose_geometry:
        issue = check_loose_geometry(collection, obj)
        if issue:
            issues.append(issue)

    if prefs.validate_check_missing_material_slot:
        issue = check_missing_material_slot(collection, obj)
        if issue:
            issues.append(issue)

    if prefs.validate_check_unused_material_slot:
        issue = check_unused_material_slot(collection, obj)
        if issue:
            issues.append(issue)

    return issues
