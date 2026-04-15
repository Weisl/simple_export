"""
Headless Blender tests for ensure_collection_properties() migration logic.

Run with:
    blender --background --python tests/blender/test_collection_setup.py

Unlike the MagicMock version these tests use real bpy.types.Collection
PropertyGroup instances, real bpy.context.scene, and real Blender property
semantics (type enforcement, default values from RNA metadata).

Covers:
  - Registered defaults match the values declared in _PRE_EXPORT_BOOL_DEFAULTS
  - Properties can be set and read back through Blender's RNA layer
  - Migration copies scene-level bool props to a collection that is still at
    its registered defaults
  - triangulate_keep_normals (default True) does NOT count as "custom"
  - Any other non-default bool value DOES block migration
  - A non-zero pre_rotate_euler blocks migration
  - Multiple collections are evaluated independently
"""

import sys
import os
import unittest
import bpy

# ---------------------------------------------------------------------------
# Bootstrap sys.path so simple_export is importable
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
from simple_export.preferences.collection_setup import (  # noqa: E402
    ensure_collection_properties,
    _PRE_EXPORT_BOOL_DEFAULTS,
    _PRE_ROTATE_EULER_DEFAULT,
)


# ---------------------------------------------------------------------------
# Module-level registration (once per Blender session)
# ---------------------------------------------------------------------------

def setUpModule():
    _h.register_collection_props()
    _h.register_scene_migration_props()


def tearDownModule():
    _h.unregister_scene_migration_props()
    _h.unregister_collection_props()


# ---------------------------------------------------------------------------
# 1. Default values via real RNA
# ---------------------------------------------------------------------------

class TestRegisteredDefaults(unittest.TestCase):
    """Verify that the PropertyGroup defaults match _PRE_EXPORT_BOOL_DEFAULTS."""

    def setUp(self):
        self.col = _h.make_collection("Defaults_Test")

    def tearDown(self):
        _h.remove_collection(self.col)

    def test_move_by_collection_offset_default_is_false(self):
        self.assertFalse(self.col.pre_export_ops.move_by_collection_offset)

    def test_triangulate_before_export_default_is_false(self):
        self.assertFalse(self.col.pre_export_ops.triangulate_before_export)

    def test_triangulate_keep_normals_default_is_true(self):
        """triangulate_keep_normals is the one bool that defaults to True."""
        self.assertTrue(self.col.pre_export_ops.triangulate_keep_normals)

    def test_apply_scale_default_is_false(self):
        self.assertFalse(self.col.pre_export_ops.apply_scale_before_export)

    def test_apply_rotation_default_is_false(self):
        self.assertFalse(self.col.pre_export_ops.apply_rotation_before_export)

    def test_apply_transform_default_is_false(self):
        self.assertFalse(self.col.pre_export_ops.apply_transform_before_export)

    def test_pre_rotate_objects_default_is_false(self):
        self.assertFalse(self.col.pre_export_ops.pre_rotate_objects)

    def test_pre_rotate_euler_default_is_zero(self):
        self.assertEqual(tuple(self.col.pre_export_ops.pre_rotate_euler), (0.0, 0.0, 0.0))

    def test_all_bool_defaults_match_constant(self):
        """Every entry in _PRE_EXPORT_BOOL_DEFAULTS matches the live PropertyGroup."""
        ops = self.col.pre_export_ops
        for attr, expected in _PRE_EXPORT_BOOL_DEFAULTS.items():
            with self.subTest(attr=attr):
                self.assertEqual(
                    getattr(ops, attr),
                    expected,
                    f"Default mismatch for {attr}: PropertyGroup={getattr(ops, attr)}, constant={expected}",
                )


# ---------------------------------------------------------------------------
# 2. Property read/write through RNA
# ---------------------------------------------------------------------------

class TestPropertyReadWrite(unittest.TestCase):
    """Setting a bool/vector on pre_export_ops must survive a read-back."""

    def setUp(self):
        self.col = _h.make_collection("RW_Test")

    def tearDown(self):
        _h.remove_collection(self.col)

    def test_set_bool_true_reads_back_true(self):
        self.col.pre_export_ops.triangulate_before_export = True
        self.assertTrue(self.col.pre_export_ops.triangulate_before_export)

    def test_set_bool_false_reads_back_false(self):
        self.col.pre_export_ops.triangulate_keep_normals = False
        self.assertFalse(self.col.pre_export_ops.triangulate_keep_normals)

    def test_set_euler_reads_back_correctly(self):
        self.col.pre_export_ops.pre_rotate_euler = (1.5, 0.0, 0.0)
        result = tuple(self.col.pre_export_ops.pre_rotate_euler)
        self.assertAlmostEqual(result[0], 1.5, places=5)
        self.assertAlmostEqual(result[1], 0.0, places=5)
        self.assertAlmostEqual(result[2], 0.0, places=5)

    def test_bool_is_enforced_as_bool(self):
        """Blender's RNA layer stores BoolProperty as a real bool."""
        self.col.pre_export_ops.move_by_collection_offset = True
        self.assertIsInstance(self.col.pre_export_ops.move_by_collection_offset, bool)


# ---------------------------------------------------------------------------
# 3. Migration: runs when collection is at defaults
# ---------------------------------------------------------------------------

class TestMigrationRuns(unittest.TestCase):
    """ensure_collection_properties() copies scene values to an unmodified collection."""

    def setUp(self):
        self.col = _h.make_collection("Migration_Run_Test")

    def tearDown(self):
        # Reset scene props to defaults before removing collection
        scene = bpy.context.scene
        for attr, default in _PRE_EXPORT_BOOL_DEFAULTS.items():
            if hasattr(scene, attr):
                setattr(scene, attr, default)
        if hasattr(scene, "pre_rotate_euler"):
            scene.pre_rotate_euler = _PRE_ROTATE_EULER_DEFAULT
        _h.remove_collection(self.col)

    def _run(self):
        ensure_collection_properties()

    def test_migration_copies_a_true_bool(self):
        bpy.context.scene.triangulate_before_export = True
        self._run()
        self.assertTrue(self.col.pre_export_ops.triangulate_before_export)

    def test_migration_copies_all_bool_props(self):
        """Every migration-source bool is copied when all collection values are default."""
        scene = bpy.context.scene
        # Flip everything except triangulate_keep_normals (whose default is True).
        overrides = {
            attr: (not default)
            for attr, default in _PRE_EXPORT_BOOL_DEFAULTS.items()
            if attr != "triangulate_keep_normals"
        }
        overrides["triangulate_keep_normals"] = False  # flip the True default
        for attr, val in overrides.items():
            setattr(scene, attr, val)

        self._run()

        ops = self.col.pre_export_ops
        for attr, val in overrides.items():
            with self.subTest(attr=attr):
                self.assertEqual(getattr(ops, attr), val,
                                 f"{attr}: expected {val}, got {getattr(ops, attr)}")

    def test_migration_copies_pre_rotate_euler(self):
        bpy.context.scene.pre_rotate_euler = (1.5, 0.0, 0.0)
        self._run()
        result = tuple(self.col.pre_export_ops.pre_rotate_euler)
        self.assertAlmostEqual(result[0], 1.5, places=5)

    def test_migration_leaves_false_bool_as_false(self):
        """Scene bool is False → collection bool stays False after migration."""
        bpy.context.scene.move_by_collection_offset = False
        self._run()
        self.assertFalse(self.col.pre_export_ops.move_by_collection_offset)


# ---------------------------------------------------------------------------
# 4. Migration: triangulate_keep_normals=True is NOT "custom"
# ---------------------------------------------------------------------------

class TestTriangulateKeepNormalsNotCustom(unittest.TestCase):
    """triangulate_keep_normals defaults to True.

    A collection where only that flag is True and everything else is at default
    must NOT be treated as "user-customised" — migration must still run.
    """

    def setUp(self):
        self.col = _h.make_collection("TriNormals_Test")

    def tearDown(self):
        scene = bpy.context.scene
        if hasattr(scene, "move_by_collection_offset"):
            scene.move_by_collection_offset = False
        _h.remove_collection(self.col)

    def test_migration_runs_when_only_default_is_true(self):
        # Verify the collection is at defaults (triangulate_keep_normals=True, rest False)
        self.assertTrue(self.col.pre_export_ops.triangulate_keep_normals)
        self.assertFalse(self.col.pre_export_ops.move_by_collection_offset)

        bpy.context.scene.move_by_collection_offset = True
        ensure_collection_properties()
        self.assertTrue(self.col.pre_export_ops.move_by_collection_offset)


# ---------------------------------------------------------------------------
# 5. Migration: skipped when any value is non-default
# ---------------------------------------------------------------------------

class TestMigrationSkipped(unittest.TestCase):
    """Migration must not overwrite a collection that already has custom values."""

    def setUp(self):
        self.col = _h.make_collection("MigSkip_Test")

    def tearDown(self):
        scene = bpy.context.scene
        for attr, default in _PRE_EXPORT_BOOL_DEFAULTS.items():
            if hasattr(scene, attr):
                setattr(scene, attr, default)
        if hasattr(scene, "pre_rotate_euler"):
            scene.pre_rotate_euler = _PRE_ROTATE_EULER_DEFAULT
        _h.remove_collection(self.col)

    def test_skipped_when_one_bool_is_non_default(self):
        # Mark the collection as already-customised
        self.col.pre_export_ops.move_by_collection_offset = True
        # Scene wants to enable something else
        bpy.context.scene.apply_scale_before_export = True

        original = self.col.pre_export_ops.apply_scale_before_export
        ensure_collection_properties()
        self.assertEqual(self.col.pre_export_ops.apply_scale_before_export, original)

    def test_skipped_when_triangulate_keep_normals_flipped_to_false(self):
        """triangulate_keep_normals=False ≠ its True default → treated as custom."""
        self.col.pre_export_ops.triangulate_keep_normals = False
        bpy.context.scene.triangulate_before_export = True

        original = self.col.pre_export_ops.triangulate_before_export
        ensure_collection_properties()
        self.assertEqual(self.col.pre_export_ops.triangulate_before_export, original)

    def test_skipped_when_euler_is_non_zero(self):
        """A non-zero pre_rotate_euler signals customisation."""
        self.col.pre_export_ops.pre_rotate_euler = (0.5, 0.0, 0.0)
        bpy.context.scene.triangulate_before_export = True

        original = self.col.pre_export_ops.triangulate_before_export
        ensure_collection_properties()
        self.assertEqual(self.col.pre_export_ops.triangulate_before_export, original)

    def test_collection_at_defaults_is_migrated_after_skip(self):
        """A second collection that IS at defaults must still be migrated even if
        another collection was skipped in the same pass."""
        col_custom = _h.make_collection("MigSkip_Custom")
        col_clean = _h.make_collection("MigSkip_Clean")
        try:
            col_custom.pre_export_ops.move_by_collection_offset = True
            bpy.context.scene.apply_rotation_before_export = True

            ensure_collection_properties()

            # The clean collection should receive the scene value
            self.assertTrue(col_clean.pre_export_ops.apply_rotation_before_export)
            # The custom collection's existing value must not change
            self.assertFalse(col_custom.pre_export_ops.apply_rotation_before_export)
        finally:
            _h.remove_collection(col_custom)
            _h.remove_collection(col_clean)


# ---------------------------------------------------------------------------
# 6. Multiple collections evaluated independently
# ---------------------------------------------------------------------------

class TestMultipleCollections(unittest.TestCase):
    """Collections at defaults are migrated; those with custom values are skipped."""

    def setUp(self):
        self.col_default = _h.make_collection("Multi_Default")
        self.col_custom = _h.make_collection("Multi_Custom")
        # Pre-customise one collection
        self.col_custom.pre_export_ops.move_by_collection_offset = True

    def tearDown(self):
        scene = bpy.context.scene
        if hasattr(scene, "apply_rotation_before_export"):
            scene.apply_rotation_before_export = False
        _h.remove_collection(self.col_default)
        _h.remove_collection(self.col_custom)

    def test_default_collection_is_migrated(self):
        bpy.context.scene.apply_rotation_before_export = True
        ensure_collection_properties()
        self.assertTrue(self.col_default.pre_export_ops.apply_rotation_before_export)

    def test_custom_collection_is_not_migrated(self):
        bpy.context.scene.apply_rotation_before_export = True
        original = self.col_custom.pre_export_ops.apply_rotation_before_export
        ensure_collection_properties()
        self.assertEqual(
            self.col_custom.pre_export_ops.apply_rotation_before_export, original
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
