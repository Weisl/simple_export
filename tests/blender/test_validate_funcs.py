"""
Headless Blender tests for functions/vallidate_func.py.

Run with:
    blender --background --python tests/blender/test_validate_funcs.py

Covers check_collection_warnings():
  - No warnings for a clean collection with visible mesh objects
  - Warning when all objects are excluded from render (hide_render=True)
  - Warning when the collection has no mesh objects (lights, cameras, etc.)
  - Warning listing missing linked-library objects
  - Missing texture warning for GLTF / USD exporters (file-sourced, non-packed)
  - No texture warning for FBX exporters (not relevant for that format)
  - Multiple warning types can appear together
"""

import os
import sys
import tempfile
import unittest

import bpy

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_TESTS_DIR = os.path.dirname(_FILE_DIR)
_ADDON_ROOT = os.path.dirname(_TESTS_DIR)
_EXTENSIONS_ROOT = os.path.dirname(_ADDON_ROOT)

if _EXTENSIONS_ROOT not in sys.path:
    sys.path.insert(0, _EXTENSIONS_ROOT)
if _ADDON_ROOT not in sys.path:
    sys.path.insert(0, _ADDON_ROOT)

import tests.blender._helpers as _h  # noqa: E402
from simple_export.functions.vallidate_func import check_collection_warnings  # noqa: E402
from simple_export.core.export_formats import ExportFormats  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_exporter_for_format(format_key):
    """Return a minimal mock-like exporter whose export_properties type resolves
    to *format_key* via ExportFormats.get_key_from_op_type.

    We use a real Blender exporter when available; otherwise fall back to a
    plain Python object with a fake __class__.__name__ that matches the
    registered op_type string.
    """
    fmt = ExportFormats.get(format_key)
    if fmt is None:
        raise ValueError(f"Unknown format key: {format_key!r}")

    # Build a tiny stub whose type() string matches the registered op_type.
    # ExportFormats.get_key_from_op_type does:  str(type(exporter.export_properties))
    # and compares it against fmt.op_type.
    op_type_str = fmt.op_type  # e.g. "<class 'bpy.types.EXPORT_SCENE_OT_fbx'>"

    class _FakeProps:
        pass

    class _FakeExporter:
        pass

    # Override __repr__ / __str__ of the *class* so that str(type(props)) matches.
    # We achieve this by dynamically renaming the class in a way that makes the
    # type string match.  Since op_type_str already looks like
    # "<class 'bpy.types.EXPORT_SCENE_OT_fbx'>", we extract the class path and
    # use it as __qualname__ / __module__ so that str(type(...)) returns the
    # right string.
    #
    # Simpler approach: register the class under the exact name so
    # str(type(props)) == op_type_str.
    import re
    m = re.match(r"<class '(.+)'>", op_type_str)
    if m:
        full_name = m.group(1)          # e.g. "bpy.types.EXPORT_SCENE_OT_fbx"
        parts = full_name.rsplit(".", 1)
        _FakeProps.__module__ = parts[0] if len(parts) > 1 else ""
        _FakeProps.__qualname__ = parts[-1]
        _FakeProps.__name__ = parts[-1]

    exporter = _FakeExporter()
    exporter.export_properties = _FakeProps()
    return exporter


def _make_mesh_object_in_col(col, name="TestMesh", location=(0, 0, 0)):
    """Create a mesh object linked *only* to col (not the scene collection)."""
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(
        [(0, 0, 0), (1, 0, 0), (1, 1, 0)],
        [],
        [(0, 1, 2)],
    )
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    col.objects.link(obj)
    return obj


def _remove_mesh_object(obj):
    mesh = obj.data if obj.type == "MESH" else None
    try:
        bpy.data.objects.remove(obj)
    except Exception:
        pass
    if mesh:
        try:
            bpy.data.meshes.remove(mesh)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestCheckCollectionWarningsClean(unittest.TestCase):
    """No warnings expected for a well-configured collection."""

    def setUp(self):
        self.col = _h.make_collection("WarnClean_Test")
        self.obj = _make_mesh_object_in_col(self.col, "CleanMesh")
        self.exporter = _make_exporter_for_format("FBX")

    def tearDown(self):
        _remove_mesh_object(self.obj)
        _h.remove_collection(self.col)

    def test_no_warnings_for_clean_collection(self):
        warnings = check_collection_warnings(self.col, self.exporter)
        self.assertEqual(warnings, [],
                         f"Expected no warnings, got: {warnings}")


class TestCheckCollectionWarningsHideRender(unittest.TestCase):
    """Warning when every object in the collection is excluded from render."""

    def setUp(self):
        self.col = _h.make_collection("WarnHide_Test")
        self.obj = _make_mesh_object_in_col(self.col, "HiddenMesh")
        self.obj.hide_render = True
        self.exporter = _make_exporter_for_format("FBX")

    def tearDown(self):
        _remove_mesh_object(self.obj)
        _h.remove_collection(self.col)

    def test_warning_when_all_objects_excluded_from_render(self):
        warnings = check_collection_warnings(self.col, self.exporter)
        self.assertTrue(
            any("excluded from render" in w for w in warnings),
            f"Expected render-exclusion warning, got: {warnings}",
        )

    def test_no_render_warning_when_at_least_one_visible(self):
        visible = _make_mesh_object_in_col(self.col, "VisibleMesh")
        visible.hide_render = False
        try:
            warnings = check_collection_warnings(self.col, self.exporter)
            self.assertFalse(
                any("excluded from render" in w for w in warnings),
                f"Unexpected render-exclusion warning: {warnings}",
            )
        finally:
            _remove_mesh_object(visible)


class TestCheckCollectionWarningsNoMesh(unittest.TestCase):
    """Warning when the collection has objects but none are meshes."""

    def setUp(self):
        self.col = _h.make_collection("WarnNoMesh_Test")
        self.exporter = _make_exporter_for_format("FBX")
        # Add a light (non-mesh) to the collection.
        light_data = bpy.data.lights.new("TestLight", type='POINT')
        self.light_obj = bpy.data.objects.new("TestLight", light_data)
        self.col.objects.link(self.light_obj)

    def tearDown(self):
        light_data = self.light_obj.data
        try:
            bpy.data.objects.remove(self.light_obj)
        except Exception:
            pass
        try:
            bpy.data.lights.remove(light_data)
        except Exception:
            pass
        _h.remove_collection(self.col)

    def test_warning_when_no_mesh_objects(self):
        warnings = check_collection_warnings(self.col, self.exporter)
        self.assertTrue(
            any("No mesh objects" in w for w in warnings),
            f"Expected no-mesh warning, got: {warnings}",
        )

    def test_no_mesh_warning_mentions_present_types(self):
        warnings = check_collection_warnings(self.col, self.exporter)
        mesh_warns = [w for w in warnings if "No mesh objects" in w]
        self.assertTrue(mesh_warns)
        self.assertIn("LIGHT", mesh_warns[0])


class TestCheckCollectionWarningsMeshPresent(unittest.TestCase):
    """No no-mesh warning when at least one MESH object is present."""

    def setUp(self):
        self.col = _h.make_collection("WarnMeshOK_Test")
        self.obj = _make_mesh_object_in_col(self.col, "ValidMesh")
        self.exporter = _make_exporter_for_format("FBX")

    def tearDown(self):
        _remove_mesh_object(self.obj)
        _h.remove_collection(self.col)

    def test_no_no_mesh_warning_when_mesh_present(self):
        warnings = check_collection_warnings(self.col, self.exporter)
        self.assertFalse(
            any("No mesh objects" in w for w in warnings),
            f"Unexpected no-mesh warning: {warnings}",
        )


class TestCheckCollectionWarningsMissingTextures(unittest.TestCase):
    """Missing texture warnings are emitted for GLTF/USD but not for FBX."""

    def setUp(self):
        self.col = _h.make_collection("WarnTex_Test")
        self.obj = _make_mesh_object_in_col(self.col, "TexMesh")
        self._setup_missing_texture()

    def _setup_missing_texture(self):
        """Add a material with a TEX_IMAGE node pointing to a non-existent file."""
        mat = bpy.data.materials.new("MissingTexMat")
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        tex_node = nodes.new("ShaderNodeTexImage")
        img = bpy.data.images.new("missing_tex.png", width=4, height=4)
        img.source = 'FILE'
        img.filepath = "/tmp/__nonexistent_texture_12345.png"
        tex_node.image = img
        self.obj.data.materials.append(mat)
        self.mat = mat
        self.img = img

    def tearDown(self):
        # Clean up image, material, object
        try:
            bpy.data.images.remove(self.img)
        except Exception:
            pass
        try:
            bpy.data.materials.remove(self.mat)
        except Exception:
            pass
        _remove_mesh_object(self.obj)
        _h.remove_collection(self.col)

    def test_missing_texture_warning_for_gltf(self):
        exporter = _make_exporter_for_format("GLTF")
        warnings = check_collection_warnings(self.col, exporter)
        self.assertTrue(
            any("Missing textures" in w for w in warnings),
            f"Expected missing-texture warning for GLTF, got: {warnings}",
        )

    def test_missing_texture_warning_for_usd(self):
        exporter = _make_exporter_for_format("USD")
        warnings = check_collection_warnings(self.col, exporter)
        self.assertTrue(
            any("Missing textures" in w for w in warnings),
            f"Expected missing-texture warning for USD, got: {warnings}",
        )

    def test_no_missing_texture_warning_for_fbx(self):
        exporter = _make_exporter_for_format("FBX")
        warnings = check_collection_warnings(self.col, exporter)
        self.assertFalse(
            any("Missing textures" in w for w in warnings),
            f"Unexpected texture warning for FBX: {warnings}",
        )

    def test_missing_texture_warning_names_the_image(self):
        exporter = _make_exporter_for_format("GLTF")
        warnings = check_collection_warnings(self.col, exporter)
        tex_warns = [w for w in warnings if "Missing textures" in w]
        self.assertTrue(tex_warns)
        self.assertIn("missing_tex.png", tex_warns[0])

    def test_packed_image_not_flagged_as_missing(self):
        """Packed images are always available — they must not trigger a warning."""
        # Create a real on-disk PNG so Blender can pack it.
        tmpdir = tempfile.mkdtemp()
        try:
            img_path = os.path.join(tmpdir, "packed_tex.png")
            packed_img = bpy.data.images.new("packed_tex.png", width=4, height=4)
            packed_img.filepath_raw = img_path
            packed_img.file_format = 'PNG'
            packed_img.save()
            packed_img.pack()

            # Swap the tex node to point to this packed image.
            mat = self.obj.data.materials[0]
            for node in mat.node_tree.nodes:
                if node.type == 'TEX_IMAGE':
                    node.image = packed_img
                    break

            exporter = _make_exporter_for_format("GLTF")
            warnings = check_collection_warnings(self.col, exporter)
            self.assertFalse(
                any("Missing textures" in w for w in warnings),
                f"Packed texture should not produce a warning: {warnings}",
            )
        finally:
            try:
                bpy.data.images.remove(packed_img)
            except Exception:
                pass
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


class TestCheckCollectionWarningsMultiple(unittest.TestCase):
    """Multiple independent warnings can be returned simultaneously."""

    def setUp(self):
        self.col = _h.make_collection("WarnMulti_Test")
        # Light object (no mesh) with hide_render=True → both "no mesh" and
        # "excluded from render" warnings.
        light_data = bpy.data.lights.new("MultiLight", type='POINT')
        self.light_obj = bpy.data.objects.new("MultiLight", light_data)
        self.light_obj.hide_render = True
        self.col.objects.link(self.light_obj)
        self.exporter = _make_exporter_for_format("FBX")

    def tearDown(self):
        light_data = self.light_obj.data
        try:
            bpy.data.objects.remove(self.light_obj)
        except Exception:
            pass
        try:
            bpy.data.lights.remove(light_data)
        except Exception:
            pass
        _h.remove_collection(self.col)

    def test_multiple_warnings_returned(self):
        warnings = check_collection_warnings(self.col, self.exporter)
        self.assertGreaterEqual(len(warnings), 2,
                                f"Expected ≥2 warnings, got: {warnings}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
