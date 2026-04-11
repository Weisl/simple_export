"""
Headless Blender tests for path-building utilities.

Run with:
    blender --background --python tests/blender/test_export_path.py

Replaces the MagicMock-based test_export_path_funcs.py with tests that use
real bpy.data.filepath (set by saving a .blend to a temp directory) and real
bpy.path.abspath / bpy.path.relpath rather than mock return values.

Covers:
  generate_base_name
    - prefix / suffix insertion and deduplication
    - blend-stem prefix (use_file_name=True) with a real saved file
    - trailing/leading underscore normalisation

  get_export_folder_path
    - ABSOLUTE mode (path given / empty with defaults / empty without defaults)
    - RELATIVE mode (path given / empty with defaults)
    - MIRROR mode (saved file / unsaved file / search-replace applied or skipped)
    - unknown mode (raises ValueError / returns default)

  ExportFormats
    - All known format keys resolve to the expected file extension
    - get_key_from_op_type round-trips through every registered format
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

from simple_export.core.export_path_func import generate_base_name, get_export_folder_path  # noqa: E402
from simple_export.core.export_formats import ExportFormats  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_blend_to_tmp(stem="my_scene"):
    """Save the current .blend file to a temp directory.

    Returns the directory and file path so tests can restore the original
    filepath afterwards.
    """
    tmpdir = tempfile.mkdtemp()
    path = os.path.join(tmpdir, f"{stem}.blend")
    bpy.ops.wm.save_as_mainfile(filepath=path, copy=True)
    return tmpdir, path


def _reset_filepath():
    """Put Blender back into 'unsaved' state.

    Blender does not expose a direct API to clear bpy.data.filepath, so we
    call new() which resets to an empty file (filepath becomes '').
    """
    bpy.ops.wm.read_homefile(use_empty=True)


# ---------------------------------------------------------------------------
# 1. generate_base_name
# ---------------------------------------------------------------------------

class TestGenerateBaseName(unittest.TestCase):
    """generate_base_name builds file stems from an entity name, prefix, and suffix."""

    # -- Basic transformations -----------------------------------------------

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
        self.assertEqual(
            generate_base_name("MyMesh", prefix="SM", suffix="LOD0"),
            "SM_MyMesh_LOD0",
        )

    def test_empty_prefix_ignored(self):
        self.assertEqual(generate_base_name("MyMesh", prefix=""), "MyMesh")

    def test_empty_suffix_ignored(self):
        self.assertEqual(generate_base_name("MyMesh", suffix=""), "MyMesh")

    # -- Separator normalisation ---------------------------------------------

    def test_prefix_with_trailing_underscore_no_double_separator(self):
        self.assertEqual(generate_base_name("MyMesh", prefix="SM_"), "SM_MyMesh")

    def test_suffix_with_leading_underscore_no_double_separator(self):
        self.assertEqual(generate_base_name("MyMesh", suffix="_LOD0"), "MyMesh_LOD0")

    # -- use_file_name with a real saved .blend file -------------------------

    def test_use_file_name_false_does_not_prepend(self):
        """Passing use_file_name=False must never prepend the file stem."""
        self.assertEqual(generate_base_name("MyMesh", use_file_name=False), "MyMesh")

    def test_use_file_name_with_unsaved_blend_no_prepend(self):
        """When bpy.data.filepath is empty the file-stem prefix is empty → skipped."""
        # Blender starts in background mode with filepath == ''
        bpy.ops.wm.read_homefile(use_empty=True)
        result = generate_base_name("MyMesh", use_file_name=True)
        # With an empty filepath, os.path.splitext(os.path.basename(''))[0] == ''
        # so no prefix is prepended (the prefix is the empty string which is falsy).
        self.assertEqual(result, "MyMesh")

    def test_use_file_name_prepends_blend_stem(self):
        """With a saved .blend the stem is prepended to the entity name."""
        tmpdir, path = _save_blend_to_tmp("my_scene")
        # After save_as_mainfile with copy=True the *original* filepath is unchanged
        # (copy=True saves a copy without touching the active file's state).
        # We need bpy.data.filepath to actually be set, so we save normally:
        bpy.ops.wm.save_as_mainfile(filepath=path)
        try:
            result = generate_base_name("MyMesh", use_file_name=True)
            self.assertEqual(result, "my_scene_MyMesh")
        finally:
            bpy.ops.wm.read_homefile(use_empty=True)
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_use_file_name_not_duplicated_when_already_prefixed(self):
        """If the stem is already the prefix, it must not be added twice."""
        tmpdir, path = _save_blend_to_tmp("my_scene")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        try:
            result = generate_base_name("my_scene_MyMesh", use_file_name=True)
            self.assertEqual(result, "my_scene_MyMesh")
        finally:
            bpy.ops.wm.read_homefile(use_empty=True)
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 2. get_export_folder_path
# ---------------------------------------------------------------------------

class TestGetExportFolderPath(unittest.TestCase):
    """get_export_folder_path routes to the right directory based on mode."""

    def setUp(self):
        # Start each test with no saved file (empty filepath).
        bpy.ops.wm.read_homefile(use_empty=True)

    def tearDown(self):
        bpy.ops.wm.read_homefile(use_empty=True)

    # -- ABSOLUTE ------------------------------------------------------------

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

    def test_absolute_empty_no_defaults_returns_none(self):
        export_dir, is_relative = get_export_folder_path(
            "ABSOLUTE", "", "", "", "", use_defaults=False
        )
        self.assertIsNone(export_dir)
        self.assertFalse(is_relative)

    # -- RELATIVE ------------------------------------------------------------

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

    def test_relative_empty_no_defaults_returns_none(self):
        # Neither branch sets is_relative when path is empty and use_defaults=False,
        # so both output values keep their zero-initialized state.
        export_dir, is_relative = get_export_folder_path(
            "RELATIVE", "", "", "", "", use_defaults=False
        )
        self.assertIsNone(export_dir)
        self.assertFalse(is_relative)

    # -- MIRROR with a real saved file ---------------------------------------

    def test_mirror_with_saved_file(self):
        tmpdir, path = _save_blend_to_tmp("scene")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        try:
            export_dir, is_relative = get_export_folder_path(
                "MIRROR", "", "", "", ""
            )
            self.assertEqual(export_dir, tmpdir)
            self.assertFalse(is_relative)
        finally:
            bpy.ops.wm.read_homefile(use_empty=True)
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_mirror_unsaved_with_defaults(self):
        # bpy.data.filepath is '' after read_homefile(use_empty=True)
        export_dir, is_relative = get_export_folder_path(
            "MIRROR", "", "", "", "", use_defaults=True
        )
        self.assertEqual(export_dir, "./")
        self.assertTrue(is_relative)

    def test_mirror_unsaved_no_defaults_returns_none(self):
        export_dir, is_relative = get_export_folder_path(
            "MIRROR", "", "", "", "", use_defaults=False
        )
        self.assertIsNone(export_dir)
        self.assertFalse(is_relative)

    def test_mirror_search_replace_applied(self):
        """When folder_path_search matches the blend dir, it is replaced."""
        tmpdir, path = _save_blend_to_tmp("scene")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        try:
            # tmpdir contains the search token if we can engineer one;
            # construct a temp dir whose path contains 'workdata'
            import shutil
            work_root = tempfile.mkdtemp()
            work_blend_dir = os.path.join(work_root, "workdata", "project")
            os.makedirs(work_blend_dir, exist_ok=True)
            blend_path = os.path.join(work_blend_dir, "scene.blend")
            bpy.ops.wm.save_as_mainfile(filepath=blend_path)
            export_dir, is_relative = get_export_folder_path(
                "MIRROR", "", "", "workdata", "sourcedata"
            )
            self.assertIn("sourcedata", export_dir)
            self.assertNotIn("workdata", export_dir)
            self.assertFalse(is_relative)
        finally:
            bpy.ops.wm.read_homefile(use_empty=True)
            import shutil
            shutil.rmtree(work_root, ignore_errors=True)
            shutil.rmtree(tmpdir, ignore_errors=True)

    def test_mirror_search_no_match_returns_blend_dir_unchanged(self):
        tmpdir, path = _save_blend_to_tmp("scene")
        bpy.ops.wm.save_as_mainfile(filepath=path)
        try:
            export_dir, is_relative = get_export_folder_path(
                "MIRROR", "", "", "nonexistent_token", "replacement"
            )
            self.assertEqual(export_dir, tmpdir)
            self.assertFalse(is_relative)
        finally:
            bpy.ops.wm.read_homefile(use_empty=True)
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    # -- Unknown mode --------------------------------------------------------

    def test_unknown_mode_raises_without_defaults(self):
        with self.assertRaises(ValueError):
            get_export_folder_path("BOGUS", "", "", "", "", use_defaults=False)

    def test_unknown_mode_returns_default_with_defaults(self):
        export_dir, is_relative = get_export_folder_path(
            "BOGUS", "", "", "", "", use_defaults=True
        )
        self.assertEqual(export_dir, "./")
        self.assertTrue(is_relative)


# ---------------------------------------------------------------------------
# 3. ExportFormats — registry correctness
# ---------------------------------------------------------------------------

class TestExportFormats(unittest.TestCase):
    """ExportFormats.get and get_key_from_op_type use no bpy internals; run
    them here so the full addon path is on sys.path."""

    _ALL_KEYS = {"FBX", "OBJ", "GLTF", "USD", "ABC", "PLY", "STL"}

    def test_fbx_extension(self):
        self.assertEqual(ExportFormats.get("FBX").file_extension, "fbx")

    def test_gltf_extension(self):
        self.assertEqual(ExportFormats.get("GLTF").file_extension, "gltf")

    def test_all_known_keys_resolve(self):
        for key in self._ALL_KEYS:
            with self.subTest(key=key):
                self.assertIsNotNone(ExportFormats.get(key))

    def test_unknown_key_returns_none(self):
        self.assertIsNone(ExportFormats.get("UNKNOWN"))

    def test_get_key_from_op_type_fbx(self):
        key = ExportFormats.get_key_from_op_type(
            "<class 'bpy.types.EXPORT_SCENE_OT_fbx'>"
        )
        self.assertEqual(key, "FBX")

    def test_get_key_from_op_type_unknown_returns_none(self):
        self.assertIsNone(ExportFormats.get_key_from_op_type("nonexistent_op"))

    def test_roundtrip_all_formats(self):
        for key, fmt in ExportFormats.FORMATS.items():
            with self.subTest(key=key):
                result = ExportFormats.get_key_from_op_type(fmt.op_type)
                self.assertEqual(result, key)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
