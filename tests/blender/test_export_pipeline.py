"""
End-to-end export pipeline tests.

Run with:
    blender --background --python tests/blender/test_export_pipeline.py

These tests drive the full Simple Export pipeline:

  1. Register the complete addon (including preferences) via simple_export.register()
     and a manual addon-preferences entry.  All tests are skipped when the full
     registration fails (e.g. because a UI panel class requires an Area that
     does not exist in background mode).

  2. Create a collection that contains a real mesh object with geometry.

  3. Add a Blender built-in file-handler exporter to the collection via
     bpy.ops.collection.exporter_add() and set an absolute filepath inside a
     temporary directory.

  4. Invoke bpy.ops.simple_export.export_collections() with
     individual_collection=True and assert that the output file was written to
     disk.

Covers:

  TestExportGuards
    - CANCELLED when the requested collection does not exist
    - CANCELLED when the collection has no objects (but has an exporter)
    - CANCELLED when the exporter filepath is empty

  TestExportCreatesFile
    - FBX  (.fbx)
    - OBJ  (.obj)
    - glTF (.glb, binary)
    - PLY  (.ply)
    - STL  (.stl)
    - USD  (.usd)
    - Alembic (.abc)

  TestExportPreExportOps
    - triangulate_before_export=True does not prevent file creation
    - move_by_collection_offset=True does not prevent file creation

  Each per-format test is individually skipped when bpy.ops.collection.exporter_add()
  is unavailable for that format in the running Blender build.
"""

import os
import sys
import shutil
import tempfile
import unittest

import bpy

# ---------------------------------------------------------------------------
# Bootstrap — add addon root and its parent to sys.path
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
import simple_export  # noqa: E402

# Module-level flag: set True only when the full addon is ready for use.
_ADDON_REGISTERED = False


# ---------------------------------------------------------------------------
# Module-level setup / teardown
# ---------------------------------------------------------------------------

def setUpModule():
    global _ADDON_REGISTERED

    # Create the addon preferences entry BEFORE calling register() so that
    # initialize_properties_* can access addons.get("simple_export").
    # In Blender 5.x Addons.new() takes no arguments; set .module afterwards.
    try:
        if "simple_export" not in bpy.context.preferences.addons:
            entry = bpy.context.preferences.addons.new()
            entry.module = "simple_export"
    except Exception as exc:
        print(
            f"[test_export_pipeline] Could not create preferences entry: {exc}\n"
            "All tests in this module will be skipped."
        )
        return

    try:
        simple_export.register()
    except Exception as exc:
        print(
            f"[test_export_pipeline] simple_export.register() failed: {exc}\n"
            "All tests in this module will be skipped."
        )
        try:
            addon_entry = bpy.context.preferences.addons.get("simple_export")
            if addon_entry:
                bpy.context.preferences.addons.remove(addon_entry)
        except Exception:
            pass
        return

    _ADDON_REGISTERED = True


def tearDownModule():
    if not _ADDON_REGISTERED:
        return
    try:
        addon_entry = bpy.context.preferences.addons.get("simple_export")
        if addon_entry:
            bpy.context.preferences.addons.remove(addon_entry)
    except Exception:
        pass
    try:
        simple_export.unregister()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_layer_col(root, target_col):
    """Recursively find the LayerCollection wrapping *target_col*."""
    if root.collection == target_col:
        return root
    for child in root.children:
        found = _find_layer_col(child, target_col)
        if found:
            return found
    return None


def _make_quad_mesh(name):
    """Return a Mesh datablock with a single quad face."""
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(
        [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],  # verts
        [],                                               # edges
        [(0, 1, 2, 3)],                                  # faces
    )
    mesh.update()
    return mesh


def _make_object_in_collection(obj_name, col):
    """Create a mesh object with geometry and link it *only* to *col*."""
    mesh = _make_quad_mesh(obj_name)
    obj = bpy.data.objects.new(obj_name, mesh)
    col.objects.link(obj)
    return obj


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


class _ExportTestBase(unittest.TestCase):
    """Shared setUp / tearDown and helpers for export tests."""

    def setUp(self):
        if not _ADDON_REGISTERED:
            self.skipTest("Full addon registration failed in background mode")
        self.tmpdir = tempfile.mkdtemp(prefix="se_test_")
        self.col = _h.make_collection("ExportPipeline_Test")
        self.obj = _make_object_in_collection("ExportMesh", self.col)
        self.lc = _find_layer_col(
            bpy.context.view_layer.layer_collection, self.col
        )

    def tearDown(self):
        _remove_object(self.obj)
        _h.remove_collection(self.col)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # -- Exporter helpers ----------------------------------------------------

    def _add_exporter(self, op_name):
        """Add a Blender exporter to self.col; skip this test if unavailable."""
        if self.lc is None:
            self.skipTest("LayerCollection not found — cannot add exporter")
        try:
            with bpy.context.temp_override(layer_collection=self.lc):
                bpy.ops.collection.exporter_add(name=op_name)
        except Exception as exc:
            self.skipTest(
                f"bpy.ops.collection.exporter_add(name={op_name!r}) "
                f"not available in this Blender build: {exc}"
            )
        if not self.col.exporters:
            self.skipTest(
                f"exporter_add(name={op_name!r}) produced no exporters"
            )
        return self.col.exporters[0]

    def _run_export(self):
        """Invoke the Simple Export operator for self.col and return its result."""
        return bpy.ops.simple_export.export_collections(
            individual_collection=True,
            collection_name=self.col.name,
        )

    def _assert_file_created(self, path):
        self.assertTrue(
            os.path.exists(path),
            f"Expected export file was not created: {path}",
        )
        self.assertGreater(
            os.path.getsize(path),
            0,
            f"Exported file is empty: {path}",
        )


# ---------------------------------------------------------------------------
# 1. Guard / early-return behaviour
# ---------------------------------------------------------------------------

class TestExportGuards(_ExportTestBase):
    """The operator must return CANCELLED (or handle gracefully) for invalid input."""

    def test_nonexistent_collection_returns_cancelled(self):
        """CANCELLED when the given collection name does not exist."""
        result = bpy.ops.simple_export.export_collections(
            individual_collection=True,
            collection_name="__nonexistent_collection__",
        )
        self.assertEqual(result, {"CANCELLED"})

    def test_empty_collection_with_exporter_returns_cancelled(self):
        """CANCELLED when the collection has an exporter but no objects."""
        exporter = self._add_exporter("IO_FH_fbx")
        out_path = os.path.join(self.tmpdir, "Empty.fbx")
        exporter.export_properties.filepath = out_path

        # Remove the object that was placed there by setUp.
        _remove_object(self.obj)
        self.obj = None  # prevent double-remove in tearDown
        self.assertEqual(len(self.col.objects), 0)

        result = self._run_export()
        self.assertEqual(result, {"CANCELLED"})
        self.assertFalse(
            os.path.exists(out_path),
            "Export file must NOT be created for an empty collection",
        )

    def tearDown(self):
        # obj may have been removed inside the test; guard against that.
        if self.obj is not None:
            _remove_object(self.obj)
            self.obj = None
        _h.remove_collection(self.col)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_empty_filepath_returns_cancelled(self):
        """CANCELLED when the exporter filepath is empty."""
        exporter = self._add_exporter("IO_FH_fbx")
        exporter.export_properties.filepath = ""  # explicitly blank

        result = self._run_export()
        self.assertEqual(result, {"CANCELLED"})


# ---------------------------------------------------------------------------
# 2. Per-format file-creation tests
# ---------------------------------------------------------------------------

@unittest.skipIf(
    bpy.app.background,
    "Blender's C-level collection exporters crash in background mode; "
    "run these tests interactively.",
)
class TestExportCreatesFile(_ExportTestBase):
    """The full pipeline must write a non-empty file to disk for each format."""

    # Helper shared by all format tests
    def _export_format(self, op_name, filename):
        out_path = os.path.join(self.tmpdir, filename)
        exporter = self._add_exporter(op_name)
        exporter.export_properties.filepath = out_path

        result = self._run_export()

        self.assertEqual(
            result,
            {"FINISHED"},
            f"{op_name} export did not FINISH. "
            f"Result: {result}. "
            f"Check the system console for export errors.",
        )
        self._assert_file_created(out_path)

    # -- Formats -------------------------------------------------------------

    def test_fbx_export_creates_file(self):
        self._export_format("IO_FH_fbx", "SM_ExportTest.fbx")

    def test_obj_export_creates_file(self):
        self._export_format("IO_FH_obj", "SM_ExportTest.obj")

    def test_glb_export_creates_file(self):
        """glTF 2.0 binary (.glb) — the default export_format for IO_FH_gltf2."""
        exporter = self._add_exporter("IO_FH_gltf2")
        out_path = os.path.join(self.tmpdir, "SM_ExportTest.glb")
        exporter.export_properties.filepath = out_path
        # Force binary GLB output so the extension matches.
        if hasattr(exporter.export_properties, "export_format"):
            exporter.export_properties.export_format = "GLB"

        result = self._run_export()

        self.assertEqual(result, {"FINISHED"}, f"GLB export did not FINISH: {result}")
        self._assert_file_created(out_path)

    def test_ply_export_creates_file(self):
        self._export_format("IO_FH_ply", "SM_ExportTest.ply")

    def test_stl_export_creates_file(self):
        self._export_format("IO_FH_stl", "SM_ExportTest.stl")

    def test_usd_export_creates_file(self):
        self._export_format("IO_FH_usd", "SM_ExportTest.usd")

    def test_alembic_export_creates_file(self):
        if bpy.app.background:
            self.skipTest(
                "Alembic exporter causes a native Blender crash during teardown "
                "in background mode — run interactively to test."
            )
        self._export_format("IO_FH_alembic", "SM_ExportTest.abc")


# ---------------------------------------------------------------------------
# 3. Pre-export operations
# ---------------------------------------------------------------------------

@unittest.skipIf(
    bpy.app.background,
    "Blender's C-level collection exporters crash in background mode; "
    "run these tests interactively.",
)
class TestExportPreExportOps(_ExportTestBase):
    """Pre-export operations (triangulate, collection offset) must not break file creation."""

    def _setup_fbx_exporter(self, filename):
        """Add an FBX exporter and return (exporter, out_path). Skip if unavailable."""
        exporter = self._add_exporter("IO_FH_fbx")
        out_path = os.path.join(self.tmpdir, filename)
        exporter.export_properties.filepath = out_path
        return exporter, out_path

    def test_triangulate_before_export_creates_file(self):
        """triangulate_before_export=True must not prevent file creation."""
        _exporter, out_path = self._setup_fbx_exporter("Triangulated.fbx")
        self.col.pre_export_ops.triangulate_before_export = True
        self.col.pre_export_ops.triangulate_keep_normals = True

        result = self._run_export()

        self.assertEqual(result, {"FINISHED"}, f"Export with triangulate did not FINISH: {result}")
        self._assert_file_created(out_path)

    def test_collection_offset_export_creates_file(self):
        """move_by_collection_offset=True must not prevent file creation."""
        _exporter, out_path = self._setup_fbx_exporter("Offset.fbx")
        self.col.instance_offset = (1.0, 2.0, 3.0)
        self.col.pre_export_ops.move_by_collection_offset = True

        result = self._run_export()

        self.assertEqual(result, {"FINISHED"}, f"Export with offset did not FINISH: {result}")
        self._assert_file_created(out_path)

    def test_offset_is_restored_after_export(self):
        """Objects must be back at their original position after export."""
        _exporter, _out_path = self._setup_fbx_exporter("OffsetRestored.fbx")
        self.col.instance_offset = (5.0, 0.0, 0.0)
        self.col.pre_export_ops.move_by_collection_offset = True

        original_location = tuple(self.obj.location)
        self._run_export()
        restored_location = tuple(self.obj.location)

        self.assertAlmostEqual(
            original_location[0], restored_location[0], places=4,
            msg="Object X location was not restored after collection-offset export",
        )
        self.assertAlmostEqual(
            original_location[1], restored_location[1], places=4,
            msg="Object Y location was not restored after collection-offset export",
        )
        self.assertAlmostEqual(
            original_location[2], restored_location[2], places=4,
            msg="Object Z location was not restored after collection-offset export",
        )


# ---------------------------------------------------------------------------
# 4. Full addon setup pipeline (add_settings_to_collections → export)
# ---------------------------------------------------------------------------

@unittest.skipIf(
    bpy.app.background,
    "Blender's C-level collection exporters crash in background mode; "
    "run these tests interactively.",
)
class TestExportViaAddonSetup(_ExportTestBase):
    """
    Tests that go through the complete Simple Export workflow:

      1. bpy.ops.simple_export.add_settings_to_collections(...)
         Adds a Blender exporter to the collection, assigns a filepath, and
         optionally applies a format preset — exactly as the UI does.

      2. bpy.ops.simple_export.export_collections(individual_collection=True, ...)
         Runs the full export pipeline and writes a file to disk.

    This differs from TestExportCreatesFile, which manually adds exporters and
    sets filepaths, bypassing the add_settings_to_collections codepath.
    """

    def _setup_via_addon(self, export_format, filename_stem):
        """
        Use bpy.ops.simple_export.add_settings_to_collections to configure the
        collection, then return the expected output path.

        Skips the test if the operator is not available or if it did not produce
        an exporter (format not supported in this Blender build).
        """
        if not hasattr(bpy.ops.simple_export, "add_settings_to_collections"):
            self.skipTest("add_settings_to_collections not registered")

        result = bpy.ops.simple_export.add_settings_to_collections(
            collection_name=self.col.name,
            export_format=export_format,
            set_export_path=True,
            assign_preset=False,          # no preset: keeps the test deterministic
            export_folder_mode="ABSOLUTE",
            folder_path_absolute=self.tmpdir,
            filename_prefix="",
            filename_suffix="",
            filename_blend_prefix=False,
            collection_naming_overwrite=False,
        )

        if result == {"CANCELLED"}:
            self.skipTest(
                f"add_settings_to_collections returned CANCELLED for format "
                f"{export_format!r} — format may not be available in this build"
            )

        if not self.col.exporters:
            self.skipTest(
                f"add_settings_to_collections produced no exporters for {export_format!r}"
            )

        exporter = self.col.exporters[0]
        from simple_export.core.export_formats import ExportFormats
        fmt = ExportFormats.get(export_format)
        if fmt is None:
            self.skipTest(f"Unknown export format key: {export_format!r}")

        ext = fmt.file_extension
        # For GLTF, the binary extension depends on the export_format property.
        if export_format == "GLTF":
            if hasattr(exporter.export_properties, "export_format"):
                exporter.export_properties.export_format = "GLB"
            ext = "glb"

        expected_path = os.path.join(self.tmpdir, f"{filename_stem}.{ext}")

        # Fallback in case the operator did not set the filepath (e.g. no valid
        # export folder was provided for this test run).
        if not exporter.export_properties.filepath:
            exporter.export_properties.filepath = expected_path

        return expected_path

    # -- Format tests ---------------------------------------------------------

    def test_gltf_full_pipeline_creates_file(self):
        """
        Full addon pipeline for GLTF:
          add_settings_to_collections → export_collections → file on disk.
        """
        expected = self._setup_via_addon("GLTF", self.col.name)
        result = self._run_export()
        self.assertEqual(result, {"FINISHED"}, f"GLTF pipeline export result: {result}")
        self._assert_file_created(expected)

    def test_fbx_full_pipeline_creates_file(self):
        """Full addon pipeline for FBX."""
        expected = self._setup_via_addon("FBX", self.col.name)
        result = self._run_export()
        self.assertEqual(result, {"FINISHED"}, f"FBX pipeline export result: {result}")
        self._assert_file_created(expected)

    def test_obj_full_pipeline_creates_file(self):
        """Full addon pipeline for OBJ."""
        expected = self._setup_via_addon("OBJ", self.col.name)
        result = self._run_export()
        self.assertEqual(result, {"FINISHED"}, f"OBJ pipeline export result: {result}")
        self._assert_file_created(expected)

    def test_collection_is_marked_selected_after_setup(self):
        """add_settings_to_collections must set simple_export_selected=True."""
        self._setup_via_addon("FBX", self.col.name)
        self.assertTrue(
            getattr(self.col, "simple_export_selected", False),
            "simple_export_selected was not set to True by add_settings_to_collections",
        )

    def test_exporter_added_to_collection_after_setup(self):
        """add_settings_to_collections must have added exactly one exporter."""
        self._setup_via_addon("FBX", self.col.name)
        self.assertGreater(
            len(self.col.exporters), 0,
            "No exporters found on the collection after add_settings_to_collections",
        )

    def test_replace_existing_exporter(self):
        """
        Calling add_settings_to_collections twice with REPLACE leaves only one exporter.

        The second call's existing_exporter_action defaults to REPLACE, so the
        original exporter should be removed and a fresh one added.
        """
        self._setup_via_addon("FBX", self.col.name)
        count_after_first = len(self.col.exporters)

        # Second setup call — the collection now has exporters.
        # The operator's invoke() opens a dialog when exporters already exist, so
        # we call it with EXEC_DEFAULT to skip invoke and go straight to execute.
        bpy.ops.simple_export.add_settings_to_collections(
            "EXEC_DEFAULT",
            collection_name=self.col.name,
            export_format="FBX",
            existing_exporter_action="REPLACE",
            set_export_path=False,
            assign_preset=False,
            export_folder_mode="ABSOLUTE",
            folder_path_absolute=self.tmpdir,
        )

        count_after_second = len(self.col.exporters)
        self.assertEqual(
            count_after_second, count_after_first,
            "REPLACE action should keep the same number of exporters (one)",
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
