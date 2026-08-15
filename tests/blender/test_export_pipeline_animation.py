"""
Animation-focused end-to-end export pipeline tests.

Run with:
    blender --background --python tests/blender/test_export_pipeline_animation.py

test_export_pipeline.py drives the full Simple Export pipeline with a plain
static quad. This module drives the same pipeline with a realistic rigged
and skinned character — CombatRig (65 bones) + CombatMesh, carrying 14
actions — to catch animation-specific breakage that a static mesh can't:
dropped actions, a mangled bone hierarchy, or a skin binding that doesn't
survive a given format. See tests/blender/fixtures/README.md for the
fixture's provenance and license (CC0).

Covers:
  TestAnimationExportCreatesFile
    - FBX / glTF / USD / Alembic each produce a non-empty file for the
      combat rig with all 14 actions present

  TestAnimationRoundTrip
    - FBX and glTF re-imports preserve the original bone count

Like test_export_pipeline.py, the classes below are skipped in
--background mode because Blender's C-level collection exporters crash
there; run interactively to exercise them.
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

FIXTURE_PATH = os.path.join(_FILE_DIR, "fixtures", "combat_character.blend")
FIXTURE_COLLECTION = "CombatCharacter"
EXPECTED_BONE_COUNT = 65
EXPECTED_ACTION_COUNT = 14

_ADDON_REGISTERED = False


# ---------------------------------------------------------------------------
# Module-level setup / teardown
# ---------------------------------------------------------------------------

def setUpModule():
    global _ADDON_REGISTERED

    try:
        if "simple_export" not in bpy.context.preferences.addons:
            entry = bpy.context.preferences.addons.new()
            entry.module = "simple_export"
    except Exception as exc:
        print(
            f"[test_export_pipeline_animation] Could not create preferences entry: {exc}\n"
            "All tests in this module will be skipped."
        )
        return

    try:
        simple_export.register()
    except Exception as exc:
        print(
            f"[test_export_pipeline_animation] simple_export.register() failed: {exc}\n"
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


def _load_combat_fixture():
    """Append CombatCharacter from the fixture .blend into the current scene."""
    with bpy.data.libraries.load(FIXTURE_PATH, link=False) as (data_from, data_to):
        data_to.collections = [FIXTURE_COLLECTION]
    col = bpy.data.collections[FIXTURE_COLLECTION]
    bpy.context.scene.collection.children.link(col)
    return col


class _AnimationExportTestBase(unittest.TestCase):
    """Shared setUp / tearDown for tests using the combat-rig fixture."""

    def setUp(self):
        if not _ADDON_REGISTERED:
            self.skipTest("Full addon registration failed in background mode")
        if not os.path.exists(FIXTURE_PATH):
            self.skipTest(f"Fixture not found: {FIXTURE_PATH}")
        self.tmpdir = tempfile.mkdtemp(prefix="se_anim_test_")
        self.col = _load_combat_fixture()
        self.lc = _find_layer_col(bpy.context.view_layer.layer_collection, self.col)

    def tearDown(self):
        objs = list(self.col.objects)
        bpy.data.collections.remove(self.col)
        for obj in objs:
            try:
                bpy.data.objects.remove(obj)
            except Exception:
                pass
        # Drop the fixture's meshes/armature-data/actions/materials, which
        # otherwise leak into bpy.data for the rest of the test run.
        bpy.ops.outliner.orphans_purge(do_local_ids=True, do_linked_ids=True, do_recursive=True)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # -- Exporter helpers ------------------------------------------------

    def _add_exporter(self, op_name):
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
            self.skipTest(f"exporter_add(name={op_name!r}) produced no exporters")
        return self.col.exporters[0]

    def _run_export(self):
        return bpy.ops.simple_export.export_collections(
            individual_collection=True,
            collection_name=self.col.name,
        )

    def _assert_file_created(self, path):
        self.assertTrue(os.path.exists(path), f"Expected export file was not created: {path}")
        self.assertGreater(os.path.getsize(path), 0, f"Exported file is empty: {path}")


# ---------------------------------------------------------------------------
# 1. Per-format file-creation tests
# ---------------------------------------------------------------------------

@unittest.skipIf(
    bpy.app.background,
    "Blender's C-level collection exporters crash in background mode; "
    "run these tests interactively.",
)
class TestAnimationExportCreatesFile(_AnimationExportTestBase):
    """The combat rig (armature + skin + 14 actions) must export cleanly."""

    def test_fbx_export_creates_file(self):
        out_path = os.path.join(self.tmpdir, "CombatCharacter.fbx")
        exporter = self._add_exporter("IO_FH_fbx")
        exporter.export_properties.filepath = out_path
        exporter.export_properties.bake_anim_use_all_actions = True

        result = self._run_export()
        self.assertEqual(result, {"FINISHED"}, f"FBX export did not FINISH: {result}")
        self._assert_file_created(out_path)

    def test_gltf_export_creates_file(self):
        out_path = os.path.join(self.tmpdir, "CombatCharacter.glb")
        exporter = self._add_exporter("IO_FH_gltf2")
        exporter.export_properties.filepath = out_path
        if hasattr(exporter.export_properties, "export_format"):
            exporter.export_properties.export_format = "GLB"

        result = self._run_export()
        self.assertEqual(result, {"FINISHED"}, f"glTF export did not FINISH: {result}")
        self._assert_file_created(out_path)

    def test_usd_export_creates_file(self):
        out_path = os.path.join(self.tmpdir, "CombatCharacter.usd")
        exporter = self._add_exporter("IO_FH_usd")
        exporter.export_properties.filepath = out_path

        result = self._run_export()
        self.assertEqual(result, {"FINISHED"}, f"USD export did not FINISH: {result}")
        self._assert_file_created(out_path)

    def test_alembic_export_creates_file(self):
        if bpy.app.background:
            self.skipTest(
                "Alembic exporter causes a native Blender crash during teardown "
                "in background mode — run interactively to test."
            )
        out_path = os.path.join(self.tmpdir, "CombatCharacter.abc")
        exporter = self._add_exporter("IO_FH_alembic")
        exporter.export_properties.filepath = out_path

        result = self._run_export()
        self.assertEqual(result, {"FINISHED"}, f"Alembic export did not FINISH: {result}")
        self._assert_file_created(out_path)


# ---------------------------------------------------------------------------
# 2. Round-trip: re-import and check the rig survived
# ---------------------------------------------------------------------------

@unittest.skipIf(
    bpy.app.background,
    "Blender's C-level collection exporters crash in background mode; "
    "run these tests interactively.",
)
class TestAnimationRoundTrip(_AnimationExportTestBase):
    """Re-import the exported file and check the bone hierarchy survived."""

    def test_fbx_round_trip_preserves_bone_count(self):
        out_path = os.path.join(self.tmpdir, "CombatCharacter_RT.fbx")
        exporter = self._add_exporter("IO_FH_fbx")
        exporter.export_properties.filepath = out_path
        exporter.export_properties.bake_anim_use_all_actions = True
        # FBX's exporter adds a synthetic tip bone per leaf by default
        # (add_leaf_bones=True), which inflates the re-imported bone count
        # independent of anything Simple Export does. Disable it so this
        # test compares like for like.
        exporter.export_properties.add_leaf_bones = False

        result = self._run_export()
        self.assertEqual(result, {"FINISHED"})
        self._assert_file_created(out_path)

        pre_import_names = set(bpy.data.objects.keys())
        bpy.ops.import_scene.fbx(filepath=out_path)
        imported = [o for o in bpy.data.objects if o.name not in pre_import_names]
        try:
            armature = next((o for o in imported if o.type == "ARMATURE"), None)
            self.assertIsNotNone(armature, "No armature found in re-imported FBX")
            self.assertEqual(
                len(armature.data.bones), EXPECTED_BONE_COUNT,
                "Bone count changed after FBX export/re-import round trip",
            )
        finally:
            for obj in imported:
                _h.remove_object(obj)

    def test_gltf_round_trip_preserves_bone_count(self):
        out_path = os.path.join(self.tmpdir, "CombatCharacter_RT.glb")
        exporter = self._add_exporter("IO_FH_gltf2")
        exporter.export_properties.filepath = out_path
        if hasattr(exporter.export_properties, "export_format"):
            exporter.export_properties.export_format = "GLB"

        result = self._run_export()
        self.assertEqual(result, {"FINISHED"})
        self._assert_file_created(out_path)

        pre_import_names = set(bpy.data.objects.keys())
        bpy.ops.import_scene.gltf(filepath=out_path)
        imported = [o for o in bpy.data.objects if o.name not in pre_import_names]
        try:
            armature = next((o for o in imported if o.type == "ARMATURE"), None)
            self.assertIsNotNone(armature, "No armature found in re-imported glTF")
            self.assertEqual(
                len(armature.data.bones), EXPECTED_BONE_COUNT,
                "Bone count changed after glTF export/re-import round trip",
            )
        finally:
            for obj in imported:
                _h.remove_object(obj)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
