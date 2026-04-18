"""
Blender script: set up a format-test scene with one cube per export format,
each in its own collection with a collection exporter pointing to //formattest/.

Run from Blender's Text Editor or:
    blender --python tests/setup_format_test_scene.py
"""

import bpy

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

EXPORT_BASE = "//formattest/"

FORMATS = [
    ("FBX",  "IO_FH_fbx",      "fbx"),
    ("OBJ",  "IO_FH_obj",      "obj"),
    ("GLTF", "IO_FH_gltf2",    "glb"),
    ("USD",  "IO_FH_usd",      "usd"),
    ("ABC",  "IO_FH_alembic",  "abc"),
    ("PLY",  "IO_FH_ply",      "ply"),
    ("STL",  "IO_FH_stl",      "stl"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_active_layer_collection(collection_name):
    """Make the layer collection with *collection_name* active."""
    def _search(layer_col):
        if layer_col.collection.name == collection_name:
            return layer_col
        for child in layer_col.children:
            found = _search(child)
            if found:
                return found
        return None

    lc = _search(bpy.context.view_layer.layer_collection)
    if lc:
        bpy.context.view_layer.active_layer_collection = lc


def _add_exporter(collection, op_name, filepath):
    """Add a collection exporter and set its filepath."""
    _set_active_layer_collection(collection.name)

    before = set(collection.exporters[:])
    bpy.ops.collection.exporter_add(name=op_name)
    after = set(collection.exporters[:])

    new_exporters = after - before
    if not new_exporters:
        print(f"  WARNING: exporter_add produced no new exporter for {collection.name}")
        return None

    exporter = new_exporters.pop()
    exporter.export_properties.filepath = filepath
    return exporter


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def setup():
    scene = bpy.context.scene

    # Parent collection that holds all format-test collections
    parent_col = bpy.data.collections.get("FormatTest")
    if parent_col is None:
        parent_col = bpy.data.collections.new("FormatTest")
        scene.collection.children.link(parent_col)

    for i, (fmt_key, op_name, ext) in enumerate(FORMATS):
        col_name = f"FormatTest_{fmt_key}"

        # Re-use existing collection or create a new one
        col = bpy.data.collections.get(col_name)
        if col is None:
            col = bpy.data.collections.new(col_name)
            parent_col.children.link(col)

        # Create cube directly inside the target collection
        cube_name = f"Cube_{fmt_key}"
        if cube_name not in bpy.data.objects:
            _set_active_layer_collection(col_name)
            x_offset = i * 2.5
            bpy.ops.mesh.primitive_cube_add(location=(x_offset, 0, 0))
            cube = bpy.context.active_object
            cube.name = cube_name

        # Remove existing exporters so we start clean
        _set_active_layer_collection(col_name)
        for _ in range(len(col.exporters)):
            bpy.ops.collection.exporter_remove(index=0)

        # Add exporter with relative path
        filepath = f"{EXPORT_BASE}{col_name}.{ext}"
        exporter = _add_exporter(col, op_name, filepath)

        status = f"path={exporter.export_properties.filepath}" if exporter else "FAILED"
        print(f"[setup_format_test_scene] {fmt_key:6s}  col={col_name}  {status}")

    print("[setup_format_test_scene] Done.")


setup()
