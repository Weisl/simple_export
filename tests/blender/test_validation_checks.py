"""
Headless Blender tests for validation/checks.py.

Run with:
    blender --background --python tests/blender/test_validation_checks.py

Covers each standalone check_* function (one flagged case + one passing case),
the four checks migrated from functions/vallidate_func.py's
check_collection_warnings(), and collect_validation_issues()'s per-object /
per-collection exception isolation and progress reporting.
"""

import os
import sys
import unittest
from types import SimpleNamespace

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
from simple_export.validation import checks as _checks  # noqa: E402
from simple_export.core.export_formats import ExportFormats  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_depsgraph():
    bpy.context.view_layer.update()
    return bpy.context.evaluated_depsgraph_get()


def _make_mesh_object(col, name, verts, faces):
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    col.objects.link(obj)
    return obj


def _make_triangle_object(col, name="Tri"):
    verts = [(0, 0, 0), (1, 0, 0), (1, 1, 0)]
    faces = [(0, 1, 2)]
    return _make_mesh_object(col, name, verts, faces)


def _make_ngon_object(col, name="Ngon"):
    verts = [(0, 0, 0), (1, 0, 0), (1.5, 1, 0), (0.5, 1.5, 0), (-0.5, 1, 0)]
    faces = [(0, 1, 2, 3, 4)]
    return _make_mesh_object(col, name, verts, faces)


def _make_loose_geo_object(col, name="LooseGeo"):
    """Triangle plus one extra unconnected vertex (loose vertex)."""
    verts = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (5, 5, 5)]
    faces = [(0, 1, 2)]
    return _make_mesh_object(col, name, verts, faces)


_CUBE_VERTS = [
    (-0.5, -0.5, -0.5), (-0.5, -0.5, 0.5), (-0.5, 0.5, -0.5), (-0.5, 0.5, 0.5),
    (0.5, -0.5, -0.5), (0.5, -0.5, 0.5), (0.5, 0.5, -0.5), (0.5, 0.5, 0.5),
]
_CUBE_FACES = (
    (0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1),
    (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3),
)


def _make_cube_object(col, name="Cube", closed=True):
    """A unit cube (12 triangles once evaluated). `closed=False` drops the
    last face, leaving an open, non-manifold boundary."""
    faces = _CUBE_FACES if closed else _CUBE_FACES[:5]
    return _make_mesh_object(col, name, _CUBE_VERTS, faces)


def _remove_object(obj):
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


def _make_exporter_for_format(format_key):
    """Return a minimal stub whose export_properties type resolves to
    `format_key` via ExportFormats.get_key_from_op_type (same trick used in
    test_validate_funcs.py's _make_exporter_for_format)."""
    fmt = ExportFormats.get(format_key)
    if fmt is None:
        raise ValueError(f"Unknown format key: {format_key!r}")

    op_type_str = fmt.op_type

    class _FakeProps:
        pass

    class _FakeExporter:
        pass

    import re
    m = re.match(r"<class '(.+)'>", op_type_str)
    if m:
        full_name = m.group(1)
        parts = full_name.rsplit(".", 1)
        _FakeProps.__module__ = parts[0] if len(parts) > 1 else ""
        _FakeProps.__qualname__ = parts[-1]
        _FakeProps.__name__ = parts[-1]

    exporter = _FakeExporter()
    exporter.export_properties = _FakeProps()
    return exporter


_ALL_CHECKS_DEFAULT = {
    'validate_check_missing_material_slot': True,
    'validate_check_negative_scale': True,
    'validate_check_missing_library_reference': True,
    'validate_check_all_objects_hidden_from_render': True,
    'validate_check_no_mesh_objects': True,
    'validate_check_missing_uv_map': True,
    'validate_check_too_many_uv_maps': True,
    'validate_check_triangle_count': True,
    'validate_check_ngons_present': True,
    'validate_check_non_manifold_geometry': True,
    'validate_check_loose_geometry': True,
    'validate_check_numeric_suffix_name': True,
    'validate_check_invalid_characters_in_name': True,
    'validate_check_missing_textures': True,
    'validate_check_unused_material_slot': True,
    'validate_check_uv_out_of_bounds': False,
    'validate_check_non_uniform_scale': False,
    'validate_check_uniform_scale_not_applied': False,
    'validation_max_triangle_count': 50000,
    'validation_max_uv_maps': 1,
}


def _make_prefs(**overrides):
    data = dict(_ALL_CHECKS_DEFAULT)
    data.update(overrides)
    return SimpleNamespace(**data)


# ---------------------------------------------------------------------------
# Object-level check tests
# ---------------------------------------------------------------------------

class TestCheckMissingMaterialSlot(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("MatSlot_Test")

    def tearDown(self):
        _h.remove_collection(self.col)

    def test_flagged_when_no_material_assigned(self):
        obj = _make_triangle_object(self.col)
        try:
            issue = _checks.check_missing_material_slot(self.col, obj)
            self.assertIsNotNone(issue)
            self.assertEqual(issue.check_id, 'missing_material_slot')
            self.assertEqual(issue.severity, 'ERROR')
        finally:
            _remove_object(obj)

    def test_passes_when_material_assigned(self):
        obj = _make_triangle_object(self.col)
        mat = bpy.data.materials.new("MatSlot_Mat")
        obj.data.materials.append(mat)
        try:
            issue = _checks.check_missing_material_slot(self.col, obj)
            self.assertIsNone(issue)
        finally:
            _remove_object(obj)
            bpy.data.materials.remove(mat)


class TestCheckNegativeScale(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("NegScale_Test")
        self.obj = _make_triangle_object(self.col)

    def tearDown(self):
        _remove_object(self.obj)
        _h.remove_collection(self.col)

    def test_flagged_for_negative_scale(self):
        self.obj.scale = (-1.0, 1.0, 1.0)
        issue = _checks.check_negative_scale(self.col, self.obj)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.severity, 'ERROR')

    def test_passes_for_positive_scale(self):
        self.obj.scale = (1.0, 1.0, 1.0)
        issue = _checks.check_negative_scale(self.col, self.obj)
        self.assertIsNone(issue)


class TestCheckMissingUVMap(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("UV_Test")
        self.obj = _make_triangle_object(self.col)

    def tearDown(self):
        _remove_object(self.obj)
        _h.remove_collection(self.col)

    def test_flagged_when_no_uv_layer(self):
        issue = _checks.check_missing_uv_map(self.col, self.obj)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.severity, 'WARNING')

    def test_passes_when_uv_layer_present(self):
        self.obj.data.uv_layers.new()
        issue = _checks.check_missing_uv_map(self.col, self.obj)
        self.assertIsNone(issue)


class TestCheckTooManyUVMaps(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("TooManyUV_Test")
        self.obj = _make_triangle_object(self.col)

    def tearDown(self):
        _remove_object(self.obj)
        _h.remove_collection(self.col)

    def test_flagged_when_over_default_limit_of_one(self):
        self.obj.data.uv_layers.new(name="UV1")
        self.obj.data.uv_layers.new(name="UV2")
        issue = _checks.check_too_many_uv_maps(self.col, self.obj, 1)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.severity, 'INFO')
        self.assertIn("2", issue.message)

    def test_passes_when_at_or_under_limit(self):
        self.obj.data.uv_layers.new(name="UV1")
        issue = _checks.check_too_many_uv_maps(self.col, self.obj, 1)
        self.assertIsNone(issue)


class TestCheckUVOutOfBounds(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("UVBounds_Test")
        self.obj = _make_triangle_object(self.col)
        self.obj.data.uv_layers.new()

    def tearDown(self):
        _remove_object(self.obj)
        _h.remove_collection(self.col)

    def test_passes_for_default_in_bounds_uvs(self):
        issue = _checks.check_uv_out_of_bounds(self.col, self.obj)
        self.assertIsNone(issue)

    def test_flagged_for_out_of_bounds_uv(self):
        uv_layer = self.obj.data.uv_layers.active
        uv_layer.data[0].uv = (1.5, 0.2)
        issue = _checks.check_uv_out_of_bounds(self.col, self.obj)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.severity, 'INFO')


class TestCheckNgonsPresent(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("Ngon_Test")

    def tearDown(self):
        _h.remove_collection(self.col)

    def test_flagged_for_pentagon_face(self):
        obj = _make_ngon_object(self.col)
        try:
            issue = _checks.check_ngons_present(self.col, obj, _get_depsgraph())
            self.assertIsNotNone(issue)
            self.assertEqual(issue.severity, 'WARNING')
        finally:
            _remove_object(obj)

    def test_passes_for_triangle_only_mesh(self):
        obj = _make_triangle_object(self.col)
        try:
            issue = _checks.check_ngons_present(self.col, obj, _get_depsgraph())
            self.assertIsNone(issue)
        finally:
            _remove_object(obj)


class TestCheckNonManifoldGeometry(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("NonManifold_Test")

    def tearDown(self):
        _h.remove_collection(self.col)

    def test_flagged_for_open_cube(self):
        obj = _make_cube_object(self.col, closed=False)
        try:
            issue = _checks.check_non_manifold_geometry(self.col, obj, _get_depsgraph())
            self.assertIsNotNone(issue)
            self.assertEqual(issue.severity, 'WARNING')
        finally:
            _remove_object(obj)

    def test_passes_for_closed_cube(self):
        obj = _make_cube_object(self.col, closed=True)
        try:
            issue = _checks.check_non_manifold_geometry(self.col, obj, _get_depsgraph())
            self.assertIsNone(issue)
        finally:
            _remove_object(obj)


class TestCheckLooseGeometry(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("Loose_Test")

    def tearDown(self):
        _h.remove_collection(self.col)

    def test_flagged_for_loose_vertex(self):
        obj = _make_loose_geo_object(self.col)
        try:
            issue = _checks.check_loose_geometry(self.col, obj)
            self.assertIsNotNone(issue)
            self.assertEqual(issue.severity, 'WARNING')
        finally:
            _remove_object(obj)

    def test_passes_for_clean_mesh(self):
        obj = _make_triangle_object(self.col)
        try:
            issue = _checks.check_loose_geometry(self.col, obj)
            self.assertIsNone(issue)
        finally:
            _remove_object(obj)


class TestCheckNumericSuffixName(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("Suffix_Test")

    def tearDown(self):
        _h.remove_collection(self.col)

    def test_flagged_for_numeric_suffix(self):
        obj = _make_triangle_object(self.col, name="SuffixTestObj.001")
        try:
            issue = _checks.check_numeric_suffix_name(self.col, obj)
            self.assertIsNotNone(issue)
            self.assertEqual(issue.severity, 'WARNING')
        finally:
            _remove_object(obj)

    def test_passes_for_plain_name(self):
        obj = _make_triangle_object(self.col, name="SuffixTestObj")
        try:
            issue = _checks.check_numeric_suffix_name(self.col, obj)
            self.assertIsNone(issue)
        finally:
            _remove_object(obj)


class TestCheckInvalidCharactersInName(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("InvalidChars_Test")

    def tearDown(self):
        _h.remove_collection(self.col)

    def test_flagged_for_spaces_and_special_characters(self):
        obj = _make_triangle_object(self.col, name="Naming Test Obj!")
        try:
            issue = _checks.check_invalid_characters_in_name(self.col, obj)
            self.assertIsNotNone(issue)
            self.assertEqual(issue.severity, 'WARNING')
            self.assertIn("space", issue.message)
        finally:
            _remove_object(obj)

    def test_passes_for_safe_name(self):
        # Dots are allowed here (the ".001" duplicate-suffix case is its own
        # dedicated check_numeric_suffix_name check), only underscore/hyphen/
        # dot/alphanumeric are exercised.
        obj = _make_triangle_object(self.col, name="Naming_Test-Obj.001")
        try:
            issue = _checks.check_invalid_characters_in_name(self.col, obj)
            self.assertIsNone(issue)
        finally:
            _remove_object(obj)


class TestCheckCollectionNameInvalidCharacters(unittest.TestCase):
    def test_flagged_for_special_characters(self):
        col = _h.make_collection("Bad Collection Name!")
        try:
            issue = _checks.check_collection_name_invalid_characters(col)
            self.assertIsNotNone(issue)
            self.assertEqual(issue.severity, 'WARNING')
        finally:
            _h.remove_collection(col)

    def test_passes_for_safe_collection_name(self):
        col = _h.make_collection("Safe_Collection_Name")
        try:
            issue = _checks.check_collection_name_invalid_characters(col)
            self.assertIsNone(issue)
        finally:
            _h.remove_collection(col)


class TestCheckUnusedMaterialSlot(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("UnusedMat_Test")
        self.obj = _make_triangle_object(self.col)
        self.used_mat = bpy.data.materials.new("UnusedMat_Used")
        self.unused_mat = bpy.data.materials.new("UnusedMat_Unused")

    def tearDown(self):
        _remove_object(self.obj)
        _h.remove_collection(self.col)
        bpy.data.materials.remove(self.used_mat)
        bpy.data.materials.remove(self.unused_mat)

    def test_flagged_for_unreferenced_slot(self):
        self.obj.data.materials.append(self.used_mat)
        self.obj.data.materials.append(self.unused_mat)  # slot 1, no polygon uses it
        issue = _checks.check_unused_material_slot(self.col, self.obj)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.severity, 'INFO')
        self.assertIn("UnusedMat_Unused", issue.message)

    def test_passes_when_only_slot_is_used(self):
        self.obj.data.materials.append(self.used_mat)
        issue = _checks.check_unused_material_slot(self.col, self.obj)
        self.assertIsNone(issue)


class TestCheckNonUniformScale(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("NonUniform_Test")
        self.obj = _make_triangle_object(self.col)

    def tearDown(self):
        _remove_object(self.obj)
        _h.remove_collection(self.col)

    def test_flagged_for_non_uniform_scale(self):
        self.obj.scale = (1.0, 2.0, 1.0)
        issue = _checks.check_non_uniform_scale(self.col, self.obj)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.severity, 'INFO')

    def test_passes_for_uniform_scale(self):
        self.obj.scale = (1.0, 1.0, 1.0)
        issue = _checks.check_non_uniform_scale(self.col, self.obj)
        self.assertIsNone(issue)


class TestCheckUniformScaleNotApplied(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("UniformNotApplied_Test")
        self.obj = _make_triangle_object(self.col)

    def tearDown(self):
        _remove_object(self.obj)
        _h.remove_collection(self.col)

    def test_flagged_for_unapplied_uniform_scale(self):
        self.obj.scale = (2.0, 2.0, 2.0)
        issue = _checks.check_uniform_scale_not_applied(self.col, self.obj)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.severity, 'INFO')

    def test_passes_for_applied_scale(self):
        self.obj.scale = (1.0, 1.0, 1.0)
        issue = _checks.check_uniform_scale_not_applied(self.col, self.obj)
        self.assertIsNone(issue)


class TestCheckTriangleCount(unittest.TestCase):
    """Collection-aggregate check: two unit cubes = 12 tris each = 24 total."""

    def setUp(self):
        self.col = _h.make_collection("TriCount_Test")
        self.obj1 = _make_cube_object(self.col, name="Cube1")
        self.obj2 = _make_cube_object(self.col, name="Cube2")

    def tearDown(self):
        _remove_object(self.obj1)
        _remove_object(self.obj2)
        _h.remove_collection(self.col)

    def test_flagged_when_over_budget(self):
        issue = _checks.check_triangle_count(self.col, 20, _get_depsgraph())
        self.assertIsNotNone(issue)
        self.assertEqual(issue.severity, 'WARNING')
        self.assertIn("24", issue.message)

    def test_passes_when_under_budget(self):
        issue = _checks.check_triangle_count(self.col, 30, _get_depsgraph())
        self.assertIsNone(issue)


# ---------------------------------------------------------------------------
# Migrated collection-level check tests
# ---------------------------------------------------------------------------

class TestCheckAllObjectsHiddenFromRender(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("Hidden_Test")
        self.obj = _make_triangle_object(self.col)

    def tearDown(self):
        _remove_object(self.obj)
        _h.remove_collection(self.col)

    def test_flagged_when_all_hidden(self):
        self.obj.hide_render = True
        issue = _checks.check_all_objects_hidden_from_render(self.col)
        self.assertIsNotNone(issue)
        # Non-blocking: the exporters still write render-hidden objects.
        self.assertEqual(issue.severity, 'WARNING')
        self.assertIn("excluded from render", issue.message)

    def test_passes_when_one_visible(self):
        self.obj.hide_render = False
        issue = _checks.check_all_objects_hidden_from_render(self.col)
        self.assertIsNone(issue)

    def test_considers_nested_subcollections(self):
        """Geometry kept in a sub-collection counts: a visible nested mesh
        means the collection is not 'all hidden', and an all-hidden nested
        mesh is flagged even with no direct objects."""
        self.obj.hide_render = True
        child = _h.make_collection("Hidden_Test_Child")
        self.col.children.link(child)
        nested = _make_triangle_object(child, name="NestedTri")
        try:
            nested.hide_render = False
            self.assertIsNone(_checks.check_all_objects_hidden_from_render(self.col))
            nested.hide_render = True
            issue = _checks.check_all_objects_hidden_from_render(self.col)
            self.assertIsNotNone(issue)
            self.assertEqual(issue.severity, 'WARNING')
        finally:
            _remove_object(nested)
            self.col.children.unlink(child)
            _h.remove_collection(child)


class TestCheckNoMeshObjects(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("NoMesh_Test")
        light_data = bpy.data.lights.new("NoMesh_Light", type='POINT')
        self.light_obj = bpy.data.objects.new("NoMesh_Light", light_data)
        self.col.objects.link(self.light_obj)

    def tearDown(self):
        light_data = self.light_obj.data
        bpy.data.objects.remove(self.light_obj)
        bpy.data.lights.remove(light_data)
        _h.remove_collection(self.col)

    def test_flagged_when_no_mesh_objects(self):
        issue = _checks.check_no_mesh_objects(self.col)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.severity, 'ERROR')
        self.assertIn("No mesh objects", issue.message)
        self.assertIn("LIGHT", issue.message)

    def test_passes_when_mesh_present(self):
        mesh_obj = _make_triangle_object(self.col)
        try:
            issue = _checks.check_no_mesh_objects(self.col)
            self.assertIsNone(issue)
        finally:
            _remove_object(mesh_obj)

    def test_passes_when_mesh_only_in_subcollection(self):
        """A collection whose only direct object is a non-mesh (e.g. a root
        empty / light) but whose sub-collection holds meshes is fine."""
        child = _h.make_collection("NoMesh_Test_Child")
        self.col.children.link(child)
        nested = _make_triangle_object(child, name="NestedMesh")
        try:
            self.assertIsNone(_checks.check_no_mesh_objects(self.col))
        finally:
            _remove_object(nested)
            self.col.children.unlink(child)
            _h.remove_collection(child)


class TestCheckMissingTextures(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("MissingTex_Test")
        self.obj = _make_triangle_object(self.col)
        mat = bpy.data.materials.new("MissingTex_Mat")
        mat.use_nodes = True
        tex_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
        img = bpy.data.images.new("missing_tex.png", width=4, height=4)
        img.source = 'FILE'
        img.filepath = "/tmp/__nonexistent_texture_validation_12345.png"
        tex_node.image = img
        self.obj.data.materials.append(mat)
        self.mat = mat
        self.img = img

    def tearDown(self):
        bpy.data.images.remove(self.img)
        bpy.data.materials.remove(self.mat)
        _remove_object(self.obj)
        _h.remove_collection(self.col)

    def test_flagged_for_gltf(self):
        exporter = _make_exporter_for_format("GLTF")
        issue = _checks.check_missing_textures(self.col, exporter)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.severity, 'WARNING')
        self.assertIn("missing_tex.png", issue.message)

    def test_not_checked_for_fbx(self):
        exporter = _make_exporter_for_format("FBX")
        issue = _checks.check_missing_textures(self.col, exporter)
        self.assertIsNone(issue)


# ---------------------------------------------------------------------------
# collect_validation_issues aggregation tests
# ---------------------------------------------------------------------------

class TestCollectValidationIssues(unittest.TestCase):
    def setUp(self):
        self.col_a = _h.make_collection("Collect_A")
        self.col_b = _h.make_collection("Collect_B")
        self.obj_a = _make_ngon_object(self.col_a, name="GoodObj")
        self.obj_b = _make_ngon_object(self.col_b, name="OtherObj")

    def tearDown(self):
        _remove_object(self.obj_a)
        _remove_object(self.obj_b)
        _h.remove_collection(self.col_a)
        _h.remove_collection(self.col_b)

    def test_disabled_checks_produce_no_issues(self):
        prefs = _make_prefs(**{k: False for k in _ALL_CHECKS_DEFAULT if k.startswith('validate_check_')})
        issues = _checks.collect_validation_issues([self.col_a], prefs, _get_depsgraph())
        self.assertEqual(issues, [])

    def test_one_bad_object_does_not_hide_others_in_same_collection(self):
        bad_obj = _make_triangle_object(self.col_a, name="BadObj")
        original = _checks.check_missing_uv_map

        def _raise_for_bad(collection, obj):
            if obj.name == "BadObj":
                raise RuntimeError("boom")
            return original(collection, obj)

        prefs = _make_prefs()
        _checks.check_missing_uv_map = _raise_for_bad
        try:
            issues = _checks.collect_validation_issues([self.col_a], prefs, _get_depsgraph())
        finally:
            _checks.check_missing_uv_map = original
            _remove_object(bad_obj)

        bad_issues = [i for i in issues if i.object_name == "BadObj"]
        good_issues = [i for i in issues if i.object_name == "GoodObj"]
        self.assertTrue(any(i.check_id == 'internal_error' for i in bad_issues))
        self.assertTrue(any(i.check_id == 'ngons_present' for i in good_issues))

    def test_one_bad_collection_does_not_hide_other_collections(self):
        original = _checks._collect_collection_issues

        def _raise_for_a(collection, prefs, depsgraph):
            if collection.name == self.col_a.name:
                raise RuntimeError("boom")
            return original(collection, prefs, depsgraph)

        prefs = _make_prefs()
        _checks._collect_collection_issues = _raise_for_a
        try:
            issues = _checks.collect_validation_issues([self.col_a, self.col_b], prefs, _get_depsgraph())
        finally:
            _checks._collect_collection_issues = original

        a_issues = [i for i in issues if i.collection_name == self.col_a.name]
        b_issues = [i for i in issues if i.collection_name == self.col_b.name]
        self.assertTrue(any(i.check_id == 'internal_error' for i in a_issues))
        self.assertTrue(any(i.check_id == 'ngons_present' for i in b_issues))

    def test_progress_callback_invoked_per_collection(self):
        calls = []
        prefs = _make_prefs()
        _checks.collect_validation_issues(
            [self.col_a, self.col_b], prefs, _get_depsgraph(),
            progress_callback=lambda done, total: calls.append((done, total)),
        )
        self.assertEqual(calls, [(1, 2), (2, 2)])


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
