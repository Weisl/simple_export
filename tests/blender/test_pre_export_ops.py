"""
Headless Blender tests for the apply_*/restore_* backup pairs in
functions/pre_export_ops.py.

Run with:
    blender --background --python tests/blender/test_pre_export_ops.py

Regression coverage for https://github.com/Weisl/simple_export/issues/306:

  Issue 3 — backup/restore keyed by obj.name (mutable)
    A depsgraph_update handler (or any code) can rename an object between
    apply_*() and restore_*(). Blender names are also freely reused once an
    object is renamed away, so a *different* object can pick up the old name.
    Both scenarios used to break the name-keyed backup dict silently.

  Issue 2 — orphaned mesh data if apply_* raises mid-function
    apply_scale/rotation/transform_for_export() used to assign the transformed
    copy to obj.data *before* recording the backup entry. If the transform
    call raised in between, obj.data was left as a partially-transformed copy
    with no backup entry to restore from — permanent corruption.

Covers:
  TestRenameBetweenApplyAndRestore
    - scale / rotation / transform / pre-rotation backups all survive a
      rename of the object performed between apply_* and restore_*.

  TestNameReuseDoesNotCrossContaminate
    - Renaming object A away and creating a new object B with A's old name
      must not cause B to receive A's backup data on restore.

  TestMidFunctionFailureDoesNotOrphanMesh
    - A forced failure inside apply_scale_for_export() (before obj.data is
      reassigned) must leave obj.data pointing at the original mesh, leave
      obj.scale unmodified, and must not leak the half-built mesh copy.

  TestNoLeakedMeshesAfterFullCycle
    - A normal, uninterrupted apply_*/restore_* cycle for scale, rotation and
      transform must not leave orphaned mesh datablocks behind.
"""

import os
import sys
import unittest
from unittest import mock

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
from simple_export.functions import pre_export_ops as peo  # noqa: E402
from simple_export.functions.pre_export_ops import (  # noqa: E402
    apply_scale_for_export, restore_scale_after_export,
    apply_rotation_for_export, restore_rotation_after_export,
    apply_transform_for_export, restore_transform_after_export,
    apply_pre_rotation, restore_pre_rotation,
    apply_triangulate_modifiers, remove_triangulate_modifiers,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_quad_mesh(name):
    mesh = bpy.data.meshes.new(name + "_mesh")
    mesh.from_pydata(
        [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
        [],
        [(0, 1, 2, 3)],
    )
    mesh.update()
    return mesh


def _make_object_in_collection(obj_name, col):
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


class _PreExportOpsTestBase(unittest.TestCase):
    def setUp(self):
        self.col = _h.make_collection("PreExportOps_Test")

    def tearDown(self):
        for obj in list(self.col.objects):
            _remove_object(obj)
        _h.remove_collection(self.col)


# ---------------------------------------------------------------------------
# Issue 3 — rename between apply and restore
# ---------------------------------------------------------------------------

class TestRenameBetweenApplyAndRestore(_PreExportOpsTestBase):
    """Backups must be keyed by a stable identity, not the mutable obj.name."""

    def test_scale_restore_survives_rename(self):
        obj = _make_object_in_collection("RenameMeScale", self.col)
        obj.scale = (2.0, 4.0, 1.0)
        original_mesh = obj.data

        backup = apply_scale_for_export(self.col)
        obj.name = "RenamedDuringExport_Scale"

        restore_scale_after_export(self.col, backup)

        self.assertEqual(tuple(obj.scale), (2.0, 4.0, 1.0))
        self.assertIs(obj.data, original_mesh)

    def test_rotation_restore_survives_rename(self):
        obj = _make_object_in_collection("RenameMeRot", self.col)
        obj.rotation_euler = (0.3, 0.0, 0.7)
        original_mesh = obj.data
        original_rotation = tuple(obj.rotation_euler)

        backup = apply_rotation_for_export(self.col)
        obj.name = "RenamedDuringExport_Rot"

        restore_rotation_after_export(self.col, backup)

        for a, b in zip(tuple(obj.rotation_euler), original_rotation):
            self.assertAlmostEqual(a, b, places=5)
        self.assertIs(obj.data, original_mesh)

    def test_transform_restore_survives_rename(self):
        obj = _make_object_in_collection("RenameMeXform", self.col)
        obj.location = (1.0, 2.0, 3.0)
        obj.rotation_euler = (0.1, 0.2, 0.3)
        obj.scale = (2.0, 2.0, 2.0)
        bpy.context.view_layer.update()
        original_mesh = obj.data
        original_matrix = obj.matrix_world.copy()

        backup = apply_transform_for_export(self.col)
        obj.name = "RenamedDuringExport_Xform"

        restore_transform_after_export(self.col, backup)

        for row_a, row_b in zip(obj.matrix_world, original_matrix):
            for a, b in zip(row_a, row_b):
                self.assertAlmostEqual(a, b, places=5)
        self.assertIs(obj.data, original_mesh)

    def test_pre_rotation_restore_survives_rename(self):
        obj = _make_object_in_collection("RenameMePreRot", self.col)
        obj.rotation_euler = (0.0, 0.0, 0.0)
        original_rotation = tuple(obj.rotation_euler)

        backup = apply_pre_rotation(self.col, (0.5, 0.0, 0.0))
        self.assertNotEqual(tuple(obj.rotation_euler), original_rotation)
        obj.name = "RenamedDuringExport_PreRot"

        restore_pre_rotation(self.col, backup)

        for a, b in zip(tuple(obj.rotation_euler), original_rotation):
            self.assertAlmostEqual(a, b, places=5)

    def test_triangulate_restore_survives_rename(self):
        obj = _make_object_in_collection("RenameMeTri", self.col)
        original_mesh = obj.data

        backup = apply_triangulate_modifiers(self.col)
        self.assertIsNot(obj.data, original_mesh, "triangulated mesh was not applied")
        obj.name = "RenamedDuringExport_Tri"

        remove_triangulate_modifiers(self.col, backup)

        self.assertIs(obj.data, original_mesh)


# ---------------------------------------------------------------------------
# Issue 3 — name reuse must not cross-contaminate a different object
# ---------------------------------------------------------------------------

class TestNameReuseDoesNotCrossContaminate(_PreExportOpsTestBase):
    """Object A renamed away, then a new object B takes A's old name.

    Restoring must apply A's backup to A (by pointer) and leave B untouched,
    even though B now carries the name the backup dict used to be keyed by.
    """

    def test_scale_backup_is_not_applied_to_a_same_named_object(self):
        obj_a = _make_object_in_collection("Original", self.col)
        obj_a.scale = (3.0, 3.0, 3.0)
        old_name = obj_a.name

        backup = apply_scale_for_export(self.col)
        obj_a.name = "OriginalMovedAside"

        obj_b = _make_object_in_collection(old_name, self.col)
        obj_b.scale = (1.0, 1.0, 1.0)
        b_scale_before_restore = tuple(obj_b.scale)
        b_mesh_before_restore = obj_b.data

        restore_scale_after_export(self.col, backup)

        # obj_b must be untouched — the backup belongs to obj_a's identity, not the name.
        self.assertEqual(tuple(obj_b.scale), b_scale_before_restore)
        self.assertIs(obj_b.data, b_mesh_before_restore)

        # obj_a must still be correctly restored via its pointer identity.
        self.assertEqual(tuple(obj_a.scale), (3.0, 3.0, 3.0))


# ---------------------------------------------------------------------------
# Issue 2 — mid-function failure must not orphan mesh data
# ---------------------------------------------------------------------------

class TestMidFunctionFailureDoesNotOrphanMesh(_PreExportOpsTestBase):
    """A failure while building the transformed copy must leave obj untouched.

    mathutils.Matrix is an immutable C type and cannot be monkeypatched
    directly, so the module-level `Matrix` name binding inside
    functions.pre_export_ops is swapped out instead — this is exactly the
    name apply_scale_for_export() calls Matrix.Diagonal() through.
    """

    def test_apply_scale_failure_leaves_object_and_data_untouched(self):
        obj = _make_object_in_collection("FailScale", self.col)
        obj.scale = (2.0, 2.0, 2.0)
        original_mesh = obj.data
        mesh_count_before = len(bpy.data.meshes)

        class _RaisingMatrix:
            Identity = staticmethod(peo.Matrix.Identity)

            @staticmethod
            def Diagonal(*_a, **_k):
                raise RuntimeError("simulated failure while building the scale matrix")

        with mock.patch.object(peo, "Matrix", _RaisingMatrix):
            with self.assertRaises(RuntimeError):
                apply_scale_for_export(self.col)

        self.assertIs(
            obj.data, original_mesh,
            "obj.data must not be reassigned when the transform build fails",
        )
        self.assertEqual(
            tuple(obj.scale), (2.0, 2.0, 2.0),
            "obj.scale must not be reset when the transform build fails",
        )
        self.assertEqual(
            len(bpy.data.meshes), mesh_count_before,
            "the half-built mesh copy must be removed, not leaked, on failure",
        )


# ---------------------------------------------------------------------------
# Regression guard — normal cycles must not leak mesh datablocks
# ---------------------------------------------------------------------------

class TestNoLeakedMeshesAfterFullCycle(_PreExportOpsTestBase):
    def test_scale_cycle_leaves_no_leaked_mesh(self):
        obj = _make_object_in_collection("CycleScale", self.col)
        obj.scale = (2.0, 1.0, 1.0)
        mesh_count_before = len(bpy.data.meshes)

        backup = apply_scale_for_export(self.col)
        restore_scale_after_export(self.col, backup)

        self.assertEqual(len(bpy.data.meshes), mesh_count_before)

    def test_rotation_cycle_leaves_no_leaked_mesh(self):
        obj = _make_object_in_collection("CycleRot", self.col)
        obj.rotation_euler = (0.2, 0.0, 0.0)
        mesh_count_before = len(bpy.data.meshes)

        backup = apply_rotation_for_export(self.col)
        restore_rotation_after_export(self.col, backup)

        self.assertEqual(len(bpy.data.meshes), mesh_count_before)

    def test_transform_cycle_leaves_no_leaked_mesh(self):
        obj = _make_object_in_collection("CycleXform", self.col)
        obj.location = (1.0, 0.0, 0.0)
        obj.scale = (2.0, 2.0, 2.0)
        mesh_count_before = len(bpy.data.meshes)

        backup = apply_transform_for_export(self.col)
        restore_transform_after_export(self.col, backup)

        self.assertEqual(len(bpy.data.meshes), mesh_count_before)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
