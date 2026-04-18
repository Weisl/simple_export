"""
Tests for pure utility functions in core/export_path_func.py and core/export_formats.py.

Covers:
  - generate_base_name: prefix/suffix/blend-stem combinations and deduplication
  - get_export_folder_path: all four modes (ABSOLUTE, RELATIVE, MIRROR, unknown)
  - ExportFormats.get and get_key_from_op_type: registry lookups and round-trips
"""

import os
import sys
import unittest

# ---------------------------------------------------------------------------
# Bootstrap: install bpy stubs and the simple_export package stub so that
# relative imports inside the addon resolve without a real Blender process.
# ---------------------------------------------------------------------------

_ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXTENSIONS_ROOT = os.path.dirname(_ADDON_ROOT)

if _EXTENSIONS_ROOT not in sys.path:
    sys.path.insert(0, _EXTENSIONS_ROOT)

from tests.bpy_stub import install as _install_bpy, make_simple_export_package

_install_bpy(blender_version=(5, 1, 0))
make_simple_export_package()

from simple_export.core.export_path_func import generate_base_name, get_export_folder_path
from simple_export.core.export_formats import ExportFormats


# ---------------------------------------------------------------------------
# 1. generate_base_name
# ---------------------------------------------------------------------------

class TestGenerateBaseName(unittest.TestCase):
    """generate_base_name builds file stems from collection name + prefix/suffix."""

    def setUp(self):
        # Give bpy.data.filepath a real string for use_file_name tests.
        sys.modules["bpy"].data.filepath = "/projects/my_scene.blend"

    def tearDown(self):
        sys.modules["bpy"].data.filepath = ""

    def test_no_modifications(self):
        self.assertEqual(generate_base_name("MyMesh"), "MyMesh")

    def test_prefix_added(self):
        self.assertEqual(generate_base_name("MyMesh", prefix="SM"), "SM_MyMesh")

    def test_prefix_not_duplicated(self):
        self.assertEqual(generate_base_name("SM_MyMesh", prefix="SM"), "SM_MyMesh")

    def test_suffix_added(self):
        self.assertEqual(generate_base_name("MyMesh", suffix="LOD0"), "MyMesh_LOD0")

    def test_suffix_not_duplicated(self):
        self.assertEqual(generate_base_name("MyMesh_LOD0", suffix="LOD0"), "MyMesh_LOD0")

    def test_prefix_and_suffix(self):
        self.assertEqual(generate_base_name("MyMesh", prefix="SM", suffix="LOD0"), "SM_MyMesh_LOD0")

    def test_empty_prefix_ignored(self):
        self.assertEqual(generate_base_name("MyMesh", prefix=""), "MyMesh")

    def test_empty_suffix_ignored(self):
        self.assertEqual(generate_base_name("MyMesh", suffix=""), "MyMesh")

    def test_use_file_name_prepends_stem(self):
        result = generate_base_name("MyMesh", use_file_name=True)
        self.assertEqual(result, "my_scene_MyMesh")

    def test_use_file_name_not_duplicated(self):
        result = generate_base_name("my_scene_MyMesh", use_file_name=True)
        self.assertEqual(result, "my_scene_MyMesh")

    def test_use_file_name_false_no_prepend(self):
        result = generate_base_name("MyMesh", use_file_name=False)
        self.assertEqual(result, "MyMesh")

    def test_use_file_name_unsaved_prepends_unsaved(self):
        sys.modules["bpy"].data.filepath = ""
        result = generate_base_name("MyMesh", use_file_name=True)
        sys.modules["bpy"].data.filepath = "/projects/my_scene.blend"
        self.assertEqual(result, "UNSAVED_MyMesh")

    def test_use_file_name_unsaved_not_duplicated(self):
        sys.modules["bpy"].data.filepath = ""
        result = generate_base_name("UNSAVED_MyMesh", use_file_name=True)
        sys.modules["bpy"].data.filepath = "/projects/my_scene.blend"
        self.assertEqual(result, "UNSAVED_MyMesh")

    def test_prefix_with_trailing_underscore_no_double_separator(self):
        self.assertEqual(generate_base_name("MyMesh", prefix="SM_"), "SM_MyMesh")

    def test_suffix_with_leading_underscore_no_double_separator(self):
        self.assertEqual(generate_base_name("MyMesh", suffix="_LOD0"), "MyMesh_LOD0")

    def test_custom_separator(self):
        self.assertEqual(generate_base_name("MyMesh", prefix="SM", separator="-"), "SM-MyMesh")

    def test_custom_separator_suffix(self):
        self.assertEqual(generate_base_name("MyMesh", suffix="LOD0", separator="-"), "MyMesh-LOD0")

    def test_empty_separator_no_sep(self):
        self.assertEqual(generate_base_name("MyMesh", prefix="SM", suffix="LOD0", separator=""), "SMMyMeshLOD0")

    def test_empty_separator_direct_concat(self):
        self.assertEqual(generate_base_name("Tank", prefix="SM", suffix="low", separator=""), "SMTanklow")

    def test_custom_separator_no_double(self):
        self.assertEqual(generate_base_name("MyMesh", prefix="SM-", separator="-"), "SM-MyMesh")


# ---------------------------------------------------------------------------
# 2. get_export_folder_path
# ---------------------------------------------------------------------------

class TestGetExportFolderPath(unittest.TestCase):
    """get_export_folder_path routes to the correct directory based on folder mode."""

    def setUp(self):
        # Default: unsaved file (empty filepath).
        sys.modules["bpy"].data.filepath = ""

    def tearDown(self):
        sys.modules["bpy"].data.filepath = ""

    # -- ABSOLUTE mode -------------------------------------------------------

    def test_absolute_with_path(self):
        export_dir, is_relative = get_export_folder_path(
            "ABSOLUTE", "/tmp/export", "", "", ""
        )
        self.assertEqual(export_dir, "/tmp/export")
        self.assertFalse(is_relative)

    def test_absolute_empty_with_defaults(self):
        export_dir, is_relative = get_export_folder_path(
            "ABSOLUTE", "", "", "", "", use_defaults=True
        )
        self.assertEqual(export_dir, "./")
        self.assertTrue(is_relative)

    def test_absolute_empty_no_defaults(self):
        # The ValueError is currently commented out; function returns (None, False).
        export_dir, is_relative = get_export_folder_path(
            "ABSOLUTE", "", "", "", "", use_defaults=False
        )
        self.assertIsNone(export_dir)
        self.assertFalse(is_relative)

    # -- RELATIVE mode -------------------------------------------------------

    def test_relative_with_path(self):
        export_dir, is_relative = get_export_folder_path(
            "RELATIVE", "", "//exports", "", ""
        )
        self.assertEqual(export_dir, "//exports")
        self.assertTrue(is_relative)

    def test_relative_empty_with_defaults(self):
        export_dir, is_relative = get_export_folder_path(
            "RELATIVE", "", "", "", "", use_defaults=True
        )
        self.assertEqual(export_dir, "//.")
        self.assertTrue(is_relative)

    # -- MIRROR mode ---------------------------------------------------------

    def test_mirror_with_saved_file(self):
        sys.modules["bpy"].data.filepath = "/home/u/proj/scene.blend"
        export_dir, is_relative = get_export_folder_path(
            "MIRROR", "", "", "", ""
        )
        self.assertEqual(export_dir, "/home/u/proj")
        self.assertFalse(is_relative)

    def test_mirror_unsaved_with_defaults(self):
        sys.modules["bpy"].data.filepath = ""
        export_dir, is_relative = get_export_folder_path(
            "MIRROR", "", "", "", "", use_defaults=True
        )
        self.assertEqual(export_dir, "./")
        self.assertTrue(is_relative)

    def test_mirror_search_replace_applied(self):
        sys.modules["bpy"].data.filepath = "/art/proj/scene.blend"
        export_dir, is_relative = get_export_folder_path(
            "MIRROR", "", "", "art", "export"
        )
        self.assertIn("/export/proj", export_dir)
        self.assertFalse(is_relative)

    def test_mirror_search_no_match(self):
        sys.modules["bpy"].data.filepath = "/home/proj/scene.blend"
        export_dir, is_relative = get_export_folder_path(
            "MIRROR", "", "", "art", "export"
        )
        self.assertEqual(export_dir, "/home/proj")
        self.assertFalse(is_relative)

    # -- Unknown mode --------------------------------------------------------

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            get_export_folder_path("BOGUS", "", "", "", "", use_defaults=False)

    def test_unknown_mode_with_defaults(self):
        export_dir, is_relative = get_export_folder_path(
            "BOGUS", "", "", "", "", use_defaults=True
        )
        self.assertEqual(export_dir, "./")
        self.assertTrue(is_relative)


# ---------------------------------------------------------------------------
# 3. ExportFormats
# ---------------------------------------------------------------------------

class TestExportFormats(unittest.TestCase):
    """ExportFormats.get and get_key_from_op_type look up formats by key / op_type."""

    _ALL_KEYS = {"FBX", "OBJ", "GLTF", "USD", "ABC", "PLY", "STL"}

    def test_get_fbx(self):
        fmt = ExportFormats.get("FBX")
        self.assertIsNotNone(fmt)
        self.assertEqual(fmt.file_extension, "fbx")

    def test_get_gltf(self):
        fmt = ExportFormats.get("GLTF")
        self.assertIsNotNone(fmt)
        self.assertEqual(fmt.file_extension, "gltf")

    def test_get_unknown_returns_none(self):
        self.assertIsNone(ExportFormats.get("UNKNOWN"))

    def test_get_all_known_formats(self):
        for key in self._ALL_KEYS:
            with self.subTest(key=key):
                self.assertIsNotNone(ExportFormats.get(key), f"Format {key!r} not found")

    def test_get_key_from_op_type_fbx(self):
        key = ExportFormats.get_key_from_op_type("<class 'bpy.types.EXPORT_SCENE_OT_fbx'>")
        self.assertEqual(key, "FBX")

    def test_get_key_from_op_type_gltf(self):
        key = ExportFormats.get_key_from_op_type("<class 'bpy.types.EXPORT_SCENE_OT_gltf'>")
        self.assertEqual(key, "GLTF")

    def test_get_key_from_op_type_unknown(self):
        self.assertIsNone(ExportFormats.get_key_from_op_type("nonexistent_op_type"))

    def test_roundtrip_all_formats(self):
        for key, fmt in ExportFormats.FORMATS.items():
            with self.subTest(key=key):
                result = ExportFormats.get_key_from_op_type(fmt.op_type)
                self.assertEqual(result, key)


if __name__ == "__main__":
    unittest.main()
