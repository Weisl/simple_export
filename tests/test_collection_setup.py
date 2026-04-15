"""
Tests for ensure_collection_properties() migration logic.

Covers:
  - Legacy scene-level pre-export ops are migrated to per-collection when all
    collection values are still at their registered defaults.
  - Migration is skipped when any bool differs from its default (user already
    customised the collection).
  - `triangulate_keep_normals` defaults to True, so a collection where only
    that flag is True (and all others are False) must NOT be treated as
    "custom" — the migration must still run.
  - A non-default `pre_rotate_euler` value blocks migration.
"""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

_ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXTENSIONS_ROOT = os.path.dirname(_ADDON_ROOT)

if _EXTENSIONS_ROOT not in sys.path:
    sys.path.insert(0, _EXTENSIONS_ROOT)

from tests.bpy_stub import install as _install_bpy, make_simple_export_package

_install_bpy(blender_version=(5, 1, 0))
make_simple_export_package()

import importlib.util as _ilutil


def _load_module(rel_path, mod_name):
    path = os.path.join(_ADDON_ROOT, rel_path)
    spec = _ilutil.spec_from_file_location(mod_name, path)
    mod = _ilutil.module_from_spec(spec)
    mod.__package__ = mod_name.rsplit(".", 1)[0]
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


_setup_mod = _load_module(
    os.path.join("preferences", "collection_setup.py"),
    "simple_export.preferences.collection_setup",
)

ensure_collection_properties = _setup_mod.ensure_collection_properties
_PRE_EXPORT_BOOL_DEFAULTS = _setup_mod._PRE_EXPORT_BOOL_DEFAULTS
_PRE_ROTATE_EULER_DEFAULT = _setup_mod._PRE_ROTATE_EULER_DEFAULT

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ops(overrides=None):
    """Return a MagicMock representing collection.pre_export_ops.

    All values start at their registered defaults; pass overrides to change
    individual fields.
    """
    ops = MagicMock()
    values = {**_PRE_EXPORT_BOOL_DEFAULTS}
    if overrides:
        values.update(overrides)
    for attr, val in values.items():
        setattr(ops, attr, val)
    ops.pre_rotate_euler = list(_PRE_ROTATE_EULER_DEFAULT)
    return ops


def _make_collection(ops=None):
    col = MagicMock()
    col.pre_export_ops = ops if ops is not None else _make_ops()
    return col


def _make_scene(**scene_attrs):
    scene = MagicMock()
    defaults = {attr: False for attr in _PRE_EXPORT_BOOL_DEFAULTS}
    defaults["pre_rotate_euler"] = list(_PRE_ROTATE_EULER_DEFAULT)
    defaults.update(scene_attrs)
    for attr, val in defaults.items():
        setattr(scene, attr, val)
    return scene


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEnsureCollectionProperties(unittest.TestCase):

    def setUp(self):
        self.bpy = sys.modules["bpy"]
        # Ensure the type guard passes
        self.bpy.types.Collection.use_root_object = MagicMock()

    def _run(self, collections, scene=None):
        ctx = MagicMock()
        ctx.scene = scene or _make_scene()
        saved = self.bpy.data.collections
        try:
            self.bpy.data.collections = collections
            self.bpy.context = ctx
            with patch.object(_setup_mod, "bpy", self.bpy):
                ensure_collection_properties()
        finally:
            self.bpy.data.collections = saved

    # ------------------------------------------------------------------
    # Migration runs when all values are at defaults
    # ------------------------------------------------------------------

    def test_migration_runs_when_all_defaults(self):
        """Scene values are copied to collection when collection is at defaults."""
        scene = _make_scene(triangulate_before_export=True)
        col = _make_collection()
        self._run([col], scene)
        self.assertTrue(col.pre_export_ops.triangulate_before_export)

    def test_migration_copies_all_bool_props(self):
        """Every bool prop from the scene is written to the collection."""
        overrides = {attr: True for attr in _PRE_EXPORT_BOOL_DEFAULTS if attr != "triangulate_keep_normals"}
        overrides["triangulate_keep_normals"] = False  # flip the one that defaults True
        scene = _make_scene(**overrides)
        col = _make_collection()
        self._run([col], scene)
        for attr, val in overrides.items():
            self.assertEqual(getattr(col.pre_export_ops, attr), val, f"mismatch on {attr}")

    def test_migration_copies_pre_rotate_euler(self):
        """pre_rotate_euler is also migrated from scene."""
        scene = _make_scene()
        scene.pre_rotate_euler = [1.5, 0.0, 0.0]
        col = _make_collection()
        self._run([col], scene)
        self.assertEqual(col.pre_export_ops.pre_rotate_euler, [1.5, 0.0, 0.0])

    # ------------------------------------------------------------------
    # triangulate_keep_normals = True is NOT treated as "custom"
    # ------------------------------------------------------------------

    def test_triangulate_keep_normals_true_at_default_does_not_block_migration(self):
        """triangulate_keep_normals defaults to True; that must not be mistaken for
        a user-set custom value that suppresses migration."""
        scene = _make_scene(move_by_collection_offset=True)
        # Collection has all defaults: triangulate_keep_normals=True, rest False.
        col = _make_collection(_make_ops())
        self._run([col], scene)
        self.assertTrue(col.pre_export_ops.move_by_collection_offset)

    # ------------------------------------------------------------------
    # Migration is skipped when any value is non-default
    # ------------------------------------------------------------------

    def test_migration_skipped_when_bool_differs_from_default(self):
        """If any bool is already non-default the collection is not overwritten."""
        scene = _make_scene(apply_scale_before_export=True)
        # Collection already has move_by_collection_offset=True (non-default).
        ops = _make_ops({"move_by_collection_offset": True})
        col = _make_collection(ops)
        original_apply_scale = col.pre_export_ops.apply_scale_before_export
        self._run([col], scene)
        # apply_scale should not have been touched
        self.assertEqual(col.pre_export_ops.apply_scale_before_export, original_apply_scale)

    def test_migration_skipped_when_triangulate_keep_normals_false(self):
        """triangulate_keep_normals=False differs from its True default → custom."""
        scene = _make_scene(triangulate_before_export=True)
        ops = _make_ops({"triangulate_keep_normals": False})
        col = _make_collection(ops)
        original = col.pre_export_ops.triangulate_before_export
        self._run([col], scene)
        self.assertEqual(col.pre_export_ops.triangulate_before_export, original)

    def test_migration_skipped_when_euler_differs_from_default(self):
        """A non-zero pre_rotate_euler signals customisation → no migration."""
        scene = _make_scene(triangulate_before_export=True)
        ops = _make_ops()
        ops.pre_rotate_euler = [0.5, 0.0, 0.0]
        col = _make_collection(ops)
        original = col.pre_export_ops.triangulate_before_export
        self._run([col], scene)
        self.assertEqual(col.pre_export_ops.triangulate_before_export, original)

    # ------------------------------------------------------------------
    # Multiple collections are each evaluated independently
    # ------------------------------------------------------------------

    def test_multiple_collections_migrated_independently(self):
        """Collections at defaults are migrated; those with custom values are skipped."""
        scene = _make_scene(apply_rotation_before_export=True)

        col_default = _make_collection()
        col_custom = _make_collection(_make_ops({"move_by_collection_offset": True}))

        original_custom_apply_rotation = col_custom.pre_export_ops.apply_rotation_before_export

        self._run([col_default, col_custom], scene)

        self.assertTrue(col_default.pre_export_ops.apply_rotation_before_export)
        self.assertEqual(
            col_custom.pre_export_ops.apply_rotation_before_export,
            original_custom_apply_rotation,
        )


if __name__ == "__main__":
    unittest.main()
