"""
Headless Blender tests for preset loading and application.

Run with:
    blender --background --python tests/blender/test_preset_application.py

These tests exercise assign_preset() and format_preset_has_changes() against
real Blender collection exporters rather than MagicMock stand-ins.

Unlike test_export_pipeline.py (which needs the full addon registered to access
addon preferences), these tests register only the minimal set of Blender types
that the preset functions actually require:

  - CollectionPreExportOps + its pointer property (from _helpers)
  - Collection.last_preset_name  (StringProperty, read by format_preset_has_changes)

This avoids the background-mode failure caused by the full addon's register()
chain accessing bpy.context.preferences.addons["simple_export"] before the
addon is in Blender's enabled list.

Covers:

  TestAssignPresetToRealExporter
    - FBX global_scale is written to exporter.export_properties
    - GLTF export_format property is applied
    - 'filepath' is never overwritten by preset application
    - 'use_selection' is never overwritten
    - Partial / old-version preset (missing some keys) does not crash
    - Preset without 'filepath' line does not raise KeyError (bug regression)

  TestPresetRoundTrip
    - Write a preset via save_export_presets → parse → apply → verify values

  TestFormatPresetHasChanges
    - Returns False when no preset name stored on the collection
    - Returns False immediately after preset is applied (values match)
    - Returns True after a tracked property is mutated
    - Returns False when the preset file no longer exists (no crash)
"""

import os
import sys
import shutil
import tempfile
import textwrap
import unittest
import unittest.mock as _mock

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


# ---------------------------------------------------------------------------
# Module-level setup / teardown
# ---------------------------------------------------------------------------

def setUpModule():
    """Register only the Blender types the preset functions actually need."""
    _h.register_collection_props()
    # format_preset_has_changes reads collection.last_preset_name via getattr
    # with a '' default, but we also want to write it in tests.
    if not hasattr(bpy.types.Collection, "last_preset_name"):
        bpy.types.Collection.last_preset_name = bpy.props.StringProperty(default="")
    if not hasattr(bpy.types.Collection, "last_addon_preset_name"):
        bpy.types.Collection.last_addon_preset_name = bpy.props.StringProperty(default="")


def tearDownModule():
    _h.unregister_collection_props()
    for attr in ("last_preset_name", "last_addon_preset_name"):
        if hasattr(bpy.types.Collection, attr):
            delattr(bpy.types.Collection, attr)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_layer_col(root, target_col):
    if root.collection == target_col:
        return root
    for child in root.children:
        found = _find_layer_col(child, target_col)
        if found:
            return found
    return None


def _write_preset_file(tmpdir, preset_name, content):
    path = os.path.join(tmpdir, f"{preset_name}.py")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(textwrap.dedent(content))
    return path


class _PresetTestBase(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="se_preset_test_")
        self.col = _h.make_collection("PresetTest")
        self.lc = _find_layer_col(
            bpy.context.view_layer.layer_collection, self.col
        )

    def tearDown(self):
        _h.remove_collection(self.col)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _add_exporter(self, op_name):
        if self.lc is None:
            self.skipTest("LayerCollection not found — cannot add exporter")
        try:
            with bpy.context.temp_override(layer_collection=self.lc):
                bpy.ops.collection.exporter_add(name=op_name)
        except Exception as exc:
            self.skipTest(
                f"bpy.ops.collection.exporter_add(name={op_name!r}) "
                f"not available: {exc}"
            )
        if not self.col.exporters:
            self.skipTest(f"exporter_add({op_name!r}) produced no exporters")
        return self.col.exporters[0]


# ---------------------------------------------------------------------------
# 1. assign_preset applied to real Blender exporters
# ---------------------------------------------------------------------------

class TestAssignPresetToRealExporter(_PresetTestBase):

    def test_fbx_scale_property_applied(self):
        """global_scale from a preset file is written to the FBX exporter."""
        exporter = self._add_exporter("IO_FH_fbx")
        if not hasattr(exporter.export_properties, "global_scale"):
            self.skipTest("FBX exporter has no global_scale in this build")

        path = _write_preset_file(self.tmpdir, "test-scale", """
            import bpy
            op = bpy.context.active_operator
            op.filepath = ''
            op.global_scale = 2.0
        """)

        from simple_export.functions.preset_func import assign_preset
        ok, msg = assign_preset(exporter, path)
        self.assertTrue(ok, f"assign_preset failed: {msg}")
        self.assertAlmostEqual(
            exporter.export_properties.global_scale, 2.0, places=4,
            msg="global_scale was not set by assign_preset",
        )

    def test_fbx_filepath_not_overwritten(self):
        """assign_preset must never touch the exporter filepath."""
        exporter = self._add_exporter("IO_FH_fbx")
        original = "/original/path.fbx"
        exporter.export_properties.filepath = original

        path = _write_preset_file(self.tmpdir, "test-fp", """
            import bpy
            op = bpy.context.active_operator
            op.filepath = '/injected/path.fbx'
            op.global_scale = 1.0
        """)

        from simple_export.functions.preset_func import assign_preset
        assign_preset(exporter, path)
        self.assertEqual(
            exporter.export_properties.filepath, original,
            "assign_preset overwrote the exporter filepath",
        )

    def test_fbx_use_selection_not_overwritten(self):
        exporter = self._add_exporter("IO_FH_fbx")
        if not hasattr(exporter.export_properties, "use_selection"):
            self.skipTest("FBX exporter has no use_selection in this build")
        exporter.export_properties.use_selection = False

        path = _write_preset_file(self.tmpdir, "test-sel", """
            import bpy
            op = bpy.context.active_operator
            op.filepath = ''
            op.use_selection = True
        """)

        from simple_export.functions.preset_func import assign_preset
        assign_preset(exporter, path)
        self.assertFalse(
            exporter.export_properties.use_selection,
            "assign_preset set use_selection to True",
        )

    def test_partial_old_version_preset_does_not_crash(self):
        """A preset missing some modern keys must not crash; defaults stay."""
        exporter = self._add_exporter("IO_FH_fbx")
        if not hasattr(exporter.export_properties, "bake_anim"):
            self.skipTest("FBX exporter has no bake_anim in this build")
        default_bake_anim = exporter.export_properties.bake_anim

        # Only sets global_scale — bake_anim absent (old version).
        path = _write_preset_file(self.tmpdir, "old-preset", """
            import bpy
            op = bpy.context.active_operator
            op.filepath = ''
            op.global_scale = 1.0
        """)

        from simple_export.functions.preset_func import assign_preset
        ok, msg = assign_preset(exporter, path)
        self.assertTrue(ok, f"assign_preset failed on partial preset: {msg}")
        self.assertEqual(
            exporter.export_properties.bake_anim,
            default_bake_anim,
            "bake_anim changed even though the preset did not mention it",
        )

    def test_preset_without_filepath_key_does_not_raise(self):
        """Regression: preset with no 'filepath' line must not raise KeyError."""
        exporter = self._add_exporter("IO_FH_fbx")
        path = _write_preset_file(self.tmpdir, "no-filepath", """
            import bpy
            op = bpy.context.active_operator
            op.global_scale = 1.0
        """)
        from simple_export.functions.preset_func import assign_preset
        try:
            ok, msg = assign_preset(exporter, path)
        except KeyError as exc:
            self.fail(f"assign_preset raised KeyError for preset without filepath: {exc}")
        self.assertTrue(ok)

    def test_gltf_export_format_property_applied(self):
        """GLTF preset can set export_format (e.g. GLB)."""
        exporter = self._add_exporter("IO_FH_gltf2")
        if not hasattr(exporter.export_properties, "export_format"):
            self.skipTest("GLTF exporter has no export_format in this build")

        path = _write_preset_file(self.tmpdir, "test-gltf", """
            import bpy
            op = bpy.context.active_operator
            op.filepath = ''
            op.export_format = 'GLB'
        """)

        from simple_export.functions.preset_func import assign_preset
        assign_preset(exporter, path)
        self.assertEqual(
            exporter.export_properties.export_format, "GLB",
            "export_format was not set to GLB by assign_preset",
        )


# ---------------------------------------------------------------------------
# 2. Round-trip: write via addon writer → parse → apply → verify
# ---------------------------------------------------------------------------

class TestPresetRoundTrip(_PresetTestBase):
    """Generate a preset file with the addon's own writer, then apply and verify."""

    def _write_ue_fbx_preset(self):
        from simple_export.presets_export import (
            get_versioned_module,
            save_export_presets,
            get_blender_version,
        )
        import importlib
        version = get_blender_version()
        mod_path = get_versioned_module(version, "fbx")
        # mod_path is e.g. ".blender_5_1.preset_data_fbx"; keep the leading "."
        # so the full absolute module path is correct.
        mod = importlib.import_module(f"simple_export.presets_export{mod_path}")
        preset_data = mod.presets_fbx["UE-fbx"]
        save_export_presets("UE-fbx", self.tmpdir, preset_data)
        return os.path.join(self.tmpdir, "UE-fbx.py"), preset_data

    def test_global_scale_round_trips(self):
        exporter = self._add_exporter("IO_FH_fbx")
        if not hasattr(exporter.export_properties, "global_scale"):
            self.skipTest("FBX exporter has no global_scale in this build")

        preset_path, preset_data = self._write_ue_fbx_preset()
        expected = preset_data["global_scale"]

        from simple_export.functions.preset_func import assign_preset
        assign_preset(exporter, preset_path)

        self.assertAlmostEqual(
            exporter.export_properties.global_scale, expected, places=4,
            msg="global_scale after round-trip does not match source preset data",
        )

    def test_axis_forward_round_trips(self):
        exporter = self._add_exporter("IO_FH_fbx")
        if not hasattr(exporter.export_properties, "axis_forward"):
            self.skipTest("FBX exporter has no axis_forward in this build")

        preset_path, preset_data = self._write_ue_fbx_preset()
        expected = preset_data["axis_forward"]

        from simple_export.functions.preset_func import assign_preset
        assign_preset(exporter, preset_path)

        self.assertEqual(
            exporter.export_properties.axis_forward, expected,
            "axis_forward after round-trip does not match source preset data",
        )

    def test_bake_anim_round_trips(self):
        exporter = self._add_exporter("IO_FH_fbx")
        if not hasattr(exporter.export_properties, "bake_anim"):
            self.skipTest("FBX exporter has no bake_anim in this build")

        preset_path, preset_data = self._write_ue_fbx_preset()
        expected = preset_data["bake_anim"]

        from simple_export.functions.preset_func import assign_preset
        assign_preset(exporter, preset_path)

        self.assertEqual(
            exporter.export_properties.bake_anim, expected,
            "bake_anim after round-trip does not match source preset data",
        )


# ---------------------------------------------------------------------------
# 3. format_preset_has_changes
# ---------------------------------------------------------------------------

class TestFormatPresetHasChanges(_PresetTestBase):
    """format_preset_has_changes detects drift between exporter and stored preset."""

    def _patch_preset_folder(self, tmpdir):
        """Context manager that redirects get_preset_format_folder to tmpdir
        and sets FBX's preset_subfolder to '' so files resolve directly.

        format_preset_has_changes imports get_preset_format_folder locally
        (inside the function body), so we patch the attribute on the *source*
        module rather than the using module's namespace.
        """
        import simple_export.presets_export.preset_format_functions as _pfm
        from simple_export.core.export_formats import ExportFormats
        orig_subfolder = ExportFormats.FORMATS["FBX"].preset_subfolder

        cm = _mock.patch.object(_pfm, "get_preset_format_folder", return_value=tmpdir)

        class _Combined:
            def __enter__(self_):
                cm.__enter__()
                ExportFormats.FORMATS["FBX"].preset_subfolder = ""
                return self_

            def __exit__(self_, *args):
                ExportFormats.FORMATS["FBX"].preset_subfolder = orig_subfolder
                cm.__exit__(*args)

        return _Combined()

    def test_no_preset_name_returns_false(self):
        exporter = self._add_exporter("IO_FH_fbx")
        self.col.last_preset_name = ""
        from simple_export.functions.preset_func import format_preset_has_changes
        self.assertFalse(format_preset_has_changes(self.col, exporter))

    def test_returns_false_right_after_apply(self):
        """Immediately after applying, exporter matches the preset → no drift."""
        exporter = self._add_exporter("IO_FH_fbx")
        if not hasattr(exporter.export_properties, "global_scale"):
            self.skipTest("FBX exporter has no global_scale in this build")

        # Write a preset whose value matches the exporter's current value exactly.
        current_scale = exporter.export_properties.global_scale
        preset_name = "exact-match"
        path = _write_preset_file(self.tmpdir, preset_name, f"""
            import bpy
            op = bpy.context.active_operator
            op.filepath = ''
            op.global_scale = {current_scale!r}
        """)
        self.col.last_preset_name = preset_name

        from simple_export.functions.preset_func import assign_preset, format_preset_has_changes
        assign_preset(exporter, path)

        with self._patch_preset_folder(self.tmpdir):
            result = format_preset_has_changes(self.col, exporter)

        self.assertFalse(result, "format_preset_has_changes returned True right after apply")

    def test_returns_true_after_property_mutated(self):
        """Changing a tracked property is detected as drift."""
        exporter = self._add_exporter("IO_FH_fbx")
        if not hasattr(exporter.export_properties, "global_scale"):
            self.skipTest("FBX exporter has no global_scale in this build")

        preset_name = "mutation-test"
        path = _write_preset_file(self.tmpdir, preset_name, """
            import bpy
            op = bpy.context.active_operator
            op.filepath = ''
            op.global_scale = 1.0
        """)
        self.col.last_preset_name = preset_name

        from simple_export.functions.preset_func import assign_preset, format_preset_has_changes
        assign_preset(exporter, path)
        exporter.export_properties.global_scale = 99.0  # drift

        with self._patch_preset_folder(self.tmpdir):
            result = format_preset_has_changes(self.col, exporter)

        self.assertTrue(result, "format_preset_has_changes did not detect mutated global_scale")

    def test_preset_file_missing_returns_false_no_crash(self):
        """Preset file deleted after assignment → treated as no drift, no crash."""
        exporter = self._add_exporter("IO_FH_fbx")
        self.col.last_preset_name = "ghost-preset"  # file never created

        from simple_export.functions.preset_func import format_preset_has_changes
        with self._patch_preset_folder(self.tmpdir):
            result = format_preset_has_changes(self.col, exporter)

        self.assertFalse(result, "Missing preset file should be treated as no changes")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
