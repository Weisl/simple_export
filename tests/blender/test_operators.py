"""
Headless Blender tests for Simple Export operators.

Run with:
    blender --background --python tests/blender/test_operators.py

Replaces the MagicMock-based test_operators.py with tests that register the
real operator classes inside Blender and invoke them through bpy.ops — the
same path Blender itself uses.  This exercises the full execute() logic on
real bpy.data.collections and bpy.data.objects rather than MagicMock stand-ins.

Operator instances are created by calling bpy.ops.<namespace>.<name>(...).
Properties are passed as keyword arguments; context overrides are applied with
bpy.context.temp_override().

Covers:
  SIMPLEEXPORT_OT_FixExportFilename
    - CANCELLED when collection does not exist
    - CANCELLED when collection has no exporters
    - Operator is findable via bpy.ops after registration

  OBJECT_OT_set_collection_offset_cursor
    - CANCELLED when collection does not exist
    - FINISHED with a real collection and real cursor location
    - Real instance_offset is updated to the cursor position
    - Offset updates when cursor moves

  OBJECT_OT_set_collection_offset_object
    - CANCELLED when collection does not exist
    - CANCELLED when no active object in context
    - FINISHED with a real collection and a real active object
    - Real instance_offset is updated to the object's location

  SIMPLEEXPORT_OT_remove_exporters
    - FINISHED even for an empty exporters list
    - Operator is findable via bpy.ops after registration
    - Exporters are cleared after add-then-remove (when exporter_add is available)

  create_root_empty_for_collection (helper function)
    - Empty created with "<collection_name>_root" name
    - Empty linked to the collection
    - collection.root_object and use_root_object set
    - Top-level objects are parented to the empty
    - Objects already with a parent are not re-parented
    - display_type and display_size are applied

  OBJECT_OT_create_root_empty (operator)
    - CANCELLED when collection does not exist
    - CANCELLED when no objects are selected
    - FINISHED with selected objects; root empty created
    - location_mode=ACTIVE_OBJECT places empty at active object location
    - location_mode=CENTER_OF_SELECTED places empty at bounding-box centre
"""

import os
import sys
import unittest
import bpy
from mathutils import Vector

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

# Module-level references filled in by setUpModule.
_fix_mod = None
_offset_mod = None
_remove_mod = None


# ---------------------------------------------------------------------------
# Module-level setup / teardown
# ---------------------------------------------------------------------------

def _load_operator_module(filename):
    import importlib.util as _ilu
    mod_name = f"simple_export.operators.{filename[:-3]}"
    sys.modules.pop(mod_name, None)
    path = os.path.join(_ADDON_ROOT, "operators", filename)
    spec = _ilu.spec_from_file_location(mod_name, path)
    mod = _ilu.module_from_spec(spec)
    mod.__package__ = "simple_export.operators"
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


class _MinimalPrefs(bpy.types.AddonPreferences):
    """Minimal addon preferences stub exposing only what collection_offset_ops needs."""
    bl_idname = "simple_export"
    root_empty_display_type: bpy.props.EnumProperty(
        name="Shape",
        items=[
            ('PLAIN_AXES', "Plain Axes", ""),
            ('CUBE', "Cube", ""),
            ('SPHERE', "Sphere", ""),
        ],
        default='PLAIN_AXES',
    )
    root_empty_display_size: bpy.props.FloatProperty(
        name="Size", default=1.0, min=0.001,
    )


def setUpModule():
    global _fix_mod, _offset_mod, _remove_mod

    # Register the scene property that operators read.
    bpy.types.Scene.export_format = bpy.props.EnumProperty(
        name="Export Format",
        items=[("FBX", "FBX", ""), ("OBJ", "OBJ", ""), ("GLTF", "glTF", "")],
        default="FBX",
    )
    _h.register_collection_props()

    # Register minimal addon preferences so operators that read
    # context.preferences.addons["simple_export"].preferences work.
    bpy.utils.register_class(_MinimalPrefs)
    if "simple_export" not in bpy.context.preferences.addons:
        entry = bpy.context.preferences.addons.new()
        entry.module = "simple_export"

    # shared_properties is imported by fix_filename — load it first.
    _load_operator_module("shared_properties.py")
    _fix_mod = _load_operator_module("fix_filename.py")
    _offset_mod = _load_operator_module("collection_offset_ops.py")
    _remove_mod = _load_operator_module("remove_exporters_ops.py")

    for mod in (_fix_mod, _offset_mod, _remove_mod):
        mod.register()


def tearDownModule():
    for mod in (_remove_mod, _offset_mod, _fix_mod):
        try:
            mod.unregister()
        except Exception:
            pass
    _h.unregister_collection_props()
    if hasattr(bpy.types.Scene, "export_format"):
        del bpy.types.Scene.export_format
    try:
        addon_entry = bpy.context.preferences.addons.get("simple_export")
        if addon_entry:
            bpy.context.preferences.addons.remove(addon_entry)
    except Exception:
        pass
    try:
        bpy.utils.unregister_class(_MinimalPrefs)
    except Exception:
        pass


# Convenience: module-level reference to the helper function under test.
def _get_create_root_empty_fn():
    return _offset_mod.create_root_empty_for_collection


# ---------------------------------------------------------------------------
# Layer-collection context helper
# ---------------------------------------------------------------------------

def _find_layer_col(root, target_col):
    """Recursively find the LayerCollection that wraps target_col."""
    if root.collection == target_col:
        return root
    for child in root.children:
        found = _find_layer_col(child, target_col)
        if found:
            return found
    return None


# ---------------------------------------------------------------------------
# 1. SIMPLEEXPORT_OT_FixExportFilename
# ---------------------------------------------------------------------------

class TestFixFilename(unittest.TestCase):

    def setUp(self):
        self.col = _h.make_collection("FixFN_Test")

    def tearDown(self):
        _h.remove_collection(self.col)

    def test_missing_collection_returns_cancelled(self):
        result = bpy.ops.simple_export.fix_export_filename(
            collection_name="__nonexistent__"
        )
        self.assertEqual(result, {"CANCELLED"})

    def test_collection_with_no_exporters_returns_cancelled(self):
        self.assertEqual(len(self.col.exporters), 0)
        result = bpy.ops.simple_export.fix_export_filename(
            collection_name=self.col.name
        )
        self.assertEqual(result, {"CANCELLED"})

    def test_operator_accessible_via_bpy_ops(self):
        self.assertTrue(
            hasattr(bpy.ops.simple_export, "fix_export_filename"),
            "bpy.ops.simple_export.fix_export_filename not found after registration",
        )


# ---------------------------------------------------------------------------
# 2. OBJECT_OT_set_collection_offset_cursor
# ---------------------------------------------------------------------------

class TestCursorOffset(unittest.TestCase):

    def setUp(self):
        self.col = _h.make_collection("CursorOff_Test")
        bpy.context.scene.cursor.location = (1.0, 2.0, 3.0)

    def tearDown(self):
        bpy.context.scene.cursor.location = (0.0, 0.0, 0.0)
        _h.remove_collection(self.col)

    def test_missing_collection_returns_cancelled(self):
        result = bpy.ops.object.set_collection_offset_cursor(
            collection_name="__nonexistent__"
        )
        self.assertEqual(result, {"CANCELLED"})

    def test_existing_collection_returns_finished(self):
        result = bpy.ops.object.set_collection_offset_cursor(
            collection_name=self.col.name
        )
        self.assertEqual(result, {"FINISHED"})

    def test_instance_offset_set_to_cursor_position(self):
        bpy.ops.object.set_collection_offset_cursor(collection_name=self.col.name)
        offset = tuple(self.col.instance_offset)
        self.assertAlmostEqual(offset[0], 1.0, places=5)
        self.assertAlmostEqual(offset[1], 2.0, places=5)
        self.assertAlmostEqual(offset[2], 3.0, places=5)

    def test_offset_tracks_cursor_position(self):
        """A second call with a different cursor position produces a different offset."""
        bpy.ops.object.set_collection_offset_cursor(collection_name=self.col.name)
        first = tuple(self.col.instance_offset)

        bpy.context.scene.cursor.location = (10.0, 20.0, 30.0)
        bpy.ops.object.set_collection_offset_cursor(collection_name=self.col.name)
        second = tuple(self.col.instance_offset)

        self.assertNotEqual(first, second)
        self.assertAlmostEqual(second[0], 10.0, places=5)
        self.assertAlmostEqual(second[1], 20.0, places=5)
        self.assertAlmostEqual(second[2], 30.0, places=5)

    def test_operator_accessible_via_bpy_ops(self):
        self.assertTrue(hasattr(bpy.ops.object, "set_collection_offset_cursor"))


# ---------------------------------------------------------------------------
# 3. OBJECT_OT_set_collection_offset_object
# ---------------------------------------------------------------------------

class TestObjectOffset(unittest.TestCase):

    def setUp(self):
        self.col = _h.make_collection("ObjOff_Test")
        self.obj = _h.make_mesh_object("OffsetTarget", location=(5.0, 6.0, 7.0))

    def tearDown(self):
        _h.remove_object(self.obj)
        _h.remove_collection(self.col)

    def test_missing_collection_returns_cancelled(self):
        with bpy.context.temp_override(object=self.obj, active_object=self.obj):
            result = bpy.ops.object.set_collection_offset_object(
                collection_name="__nonexistent__"
            )
        self.assertEqual(result, {"CANCELLED"})

    def test_no_active_object_returns_cancelled(self):
        with bpy.context.temp_override(object=None, active_object=None):
            result = bpy.ops.object.set_collection_offset_object(
                collection_name=self.col.name
            )
        self.assertEqual(result, {"CANCELLED"})

    def test_happy_path_returns_finished(self):
        with bpy.context.temp_override(object=self.obj, active_object=self.obj):
            result = bpy.ops.object.set_collection_offset_object(
                collection_name=self.col.name
            )
        self.assertEqual(result, {"FINISHED"})

    def test_instance_offset_set_to_object_location(self):
        with bpy.context.temp_override(object=self.obj, active_object=self.obj):
            bpy.ops.object.set_collection_offset_object(
                collection_name=self.col.name
            )
        offset = tuple(self.col.instance_offset)
        self.assertAlmostEqual(offset[0], 5.0, places=5)
        self.assertAlmostEqual(offset[1], 6.0, places=5)
        self.assertAlmostEqual(offset[2], 7.0, places=5)

    def test_offset_reflects_moved_object(self):
        """Moving the object before invocation must change the stored offset."""
        self.obj.location = (99.0, 0.0, 0.0)
        with bpy.context.temp_override(object=self.obj, active_object=self.obj):
            bpy.ops.object.set_collection_offset_object(
                collection_name=self.col.name
            )
        offset = tuple(self.col.instance_offset)
        self.assertAlmostEqual(offset[0], 99.0, places=5)

    def test_operator_accessible_via_bpy_ops(self):
        self.assertTrue(hasattr(bpy.ops.object, "set_collection_offset_object"))


# ---------------------------------------------------------------------------
# 4. SIMPLEEXPORT_OT_remove_exporters
# ---------------------------------------------------------------------------

class TestRemoveExporters(unittest.TestCase):

    def setUp(self):
        self.col = _h.make_collection("RemExp_Test")

    def tearDown(self):
        _h.remove_collection(self.col)

    def test_empty_exporters_returns_finished(self):
        """remove_exporters on a collection with no exporters must still FINISH."""
        self.assertEqual(len(self.col.exporters), 0)
        result = bpy.ops.simple_export.remove_exporters(
            collection_name=self.col.name
        )
        self.assertEqual(result, {"FINISHED"})

    def test_operator_accessible_via_bpy_ops(self):
        self.assertTrue(hasattr(bpy.ops.simple_export, "remove_exporters"))

    def test_exporters_cleared_after_add_and_remove(self):
        """Add a real exporter then verify remove_exporters clears it.

        Skipped if bpy.ops.collection.exporter_add is unavailable in
        background context (no active layer collection).
        """
        lc = _find_layer_col(bpy.context.view_layer.layer_collection, self.col)
        if lc is None:
            self.skipTest("Could not find layer_collection for the test collection")

        try:
            with bpy.context.temp_override(layer_collection=lc):
                bpy.ops.collection.exporter_add(name="ExportFBX")
        except Exception as exc:
            self.skipTest(f"bpy.ops.collection.exporter_add not available: {exc}")

        self.assertGreater(len(self.col.exporters), 0, "Exporter was not added")

        with bpy.context.temp_override(layer_collection=lc):
            bpy.ops.simple_export.remove_exporters(collection_name=self.col.name)

        self.assertEqual(len(self.col.exporters), 0, "Exporter was not removed")

    def test_fix_filename_finished_after_exporter_added(self):
        """With a real FBX exporter present, fix_export_filename must FINISH.

        Skipped if exporter_add is unavailable in background context.
        """
        lc = _find_layer_col(bpy.context.view_layer.layer_collection, self.col)
        if lc is None:
            self.skipTest("Could not find layer_collection for the test collection")

        try:
            with bpy.context.temp_override(layer_collection=lc):
                bpy.ops.collection.exporter_add(name="ExportFBX")
        except Exception as exc:
            self.skipTest(f"bpy.ops.collection.exporter_add not available: {exc}")

        if not self.col.exporters:
            self.skipTest("No exporter was added; skipping happy-path test")

        # Ensure the exporter has a valid filepath to manipulate.
        exporter = self.col.exporters[0]
        exporter.export_properties.filepath = "/tmp/exports/OldName.fbx"

        bpy.context.scene.export_format = "FBX"
        result = bpy.ops.simple_export.fix_export_filename(
            collection_name=self.col.name,
            filename_prefix="SM",
            filename_suffix="",
            filename_blend_prefix=False,
        )
        self.assertEqual(result, {"FINISHED"})

        # Verify the filename was updated.
        new_path = self.col.exporters[0].export_properties.filepath
        self.assertIn("SM_", new_path)

        # Cleanup
        with bpy.context.temp_override(layer_collection=lc):
            bpy.ops.simple_export.remove_exporters(collection_name=self.col.name)


# ---------------------------------------------------------------------------
# 5. create_root_empty_for_collection (helper function)
# ---------------------------------------------------------------------------

class TestCreateRootEmptyHelper(unittest.TestCase):
    """create_root_empty_for_collection creates and wires up an EMPTY object."""

    def setUp(self):
        self.col = _h.make_collection("RootEmpty_Helper_Test")

    def tearDown(self):
        # Remove objects that may have been added.
        for obj in list(bpy.data.objects):
            if obj.name.endswith("_root") and "_root" in obj.name:
                try:
                    bpy.data.objects.remove(obj)
                except Exception:
                    pass
        _h.remove_collection(self.col)

    def test_empty_created_with_correct_name(self):
        fn = _get_create_root_empty_fn()
        empty = fn(self.col, Vector((0, 0, 0)))
        self.assertEqual(empty.name, self.col.name + "_root")

    def test_empty_linked_to_collection(self):
        fn = _get_create_root_empty_fn()
        empty = fn(self.col, Vector((0, 0, 0)))
        self.assertIn(empty, list(self.col.objects))

    def test_use_root_object_set_true(self):
        fn = _get_create_root_empty_fn()
        fn(self.col, Vector((0, 0, 0)))
        self.assertTrue(self.col.use_root_object)

    def test_root_object_assigned_to_empty(self):
        fn = _get_create_root_empty_fn()
        empty = fn(self.col, Vector((0, 0, 0)))
        self.assertIs(self.col.root_object, empty)

    def test_top_level_object_parented_to_empty(self):
        """Objects with no parent should become children of the root empty."""
        obj = _h.make_mesh_object("RootChild", location=(1, 2, 3))
        try:
            fn = _get_create_root_empty_fn()
            empty = fn(self.col, Vector((0, 0, 0)), objects_to_parent=[obj])
            self.assertIs(obj.parent, empty)
        finally:
            _h.remove_object(obj)

    def test_already_parented_object_not_reparented(self):
        """An object that already has a parent must be skipped."""
        parent_obj = _h.make_mesh_object("ExistingParent", location=(0, 0, 0))
        child_obj = _h.make_mesh_object("AlreadyParented", location=(1, 0, 0))
        child_obj.parent = parent_obj
        try:
            fn = _get_create_root_empty_fn()
            fn(self.col, Vector((0, 0, 0)), objects_to_parent=[child_obj])
            self.assertIs(child_obj.parent, parent_obj,
                          "Already-parented object must not be re-parented")
        finally:
            child_obj.parent = None
            _h.remove_object(child_obj)
            _h.remove_object(parent_obj)

    def test_display_type_applied(self):
        fn = _get_create_root_empty_fn()
        empty = fn(self.col, Vector((0, 0, 0)), display_type='CUBE')
        self.assertEqual(empty.empty_display_type, 'CUBE')

    def test_display_size_applied(self):
        fn = _get_create_root_empty_fn()
        empty = fn(self.col, Vector((0, 0, 0)), display_size=2.5)
        self.assertAlmostEqual(empty.empty_display_size, 2.5, places=4)

    def test_location_applied(self):
        fn = _get_create_root_empty_fn()
        empty = fn(self.col, Vector((3.0, 4.0, 5.0)))
        self.assertAlmostEqual(empty.location.x, 3.0, places=4)
        self.assertAlmostEqual(empty.location.y, 4.0, places=4)
        self.assertAlmostEqual(empty.location.z, 5.0, places=4)

    def test_no_objects_to_parent_creates_empty_only(self):
        """Calling with objects_to_parent=None must not raise."""
        fn = _get_create_root_empty_fn()
        empty = fn(self.col, Vector((0, 0, 0)), objects_to_parent=None)
        self.assertIsNotNone(empty)


# ---------------------------------------------------------------------------
# 6. OBJECT_OT_create_root_empty (operator via bpy.ops)
# ---------------------------------------------------------------------------

class TestCreateRootEmptyOperator(unittest.TestCase):
    """OBJECT_OT_create_root_empty: operator-level integration tests."""

    def setUp(self):
        self.col = _h.make_collection("RootEmpty_Op_Test")

    def tearDown(self):
        for obj in list(bpy.data.objects):
            if "_root" in obj.name:
                try:
                    bpy.data.objects.remove(obj)
                except Exception:
                    pass
        for obj in list(bpy.data.objects):
            if obj.name.startswith("OpTarget"):
                try:
                    bpy.data.objects.remove(obj)
                except Exception:
                    pass
        _h.remove_collection(self.col)

    def test_missing_collection_returns_cancelled(self):
        obj = _h.make_mesh_object("OpTarget_miss", location=(0, 0, 0))
        try:
            with bpy.context.temp_override(
                selected_objects=[obj], active_object=obj
            ):
                result = bpy.ops.object.create_root_empty(
                    collection_name="__nonexistent__"
                )
            self.assertEqual(result, {"CANCELLED"})
        finally:
            _h.remove_object(obj)

    def test_no_selected_objects_returns_cancelled(self):
        with bpy.context.temp_override(selected_objects=[], active_object=None):
            result = bpy.ops.object.create_root_empty(
                collection_name=self.col.name
            )
        self.assertEqual(result, {"CANCELLED"})

    def test_active_object_mode_places_empty_at_active_location(self):
        obj = _h.make_mesh_object("OpTarget_active", location=(7.0, 8.0, 9.0))
        self.col.objects.link(obj)
        try:
            with bpy.context.temp_override(
                selected_objects=[obj], active_object=obj
            ):
                result = bpy.ops.object.create_root_empty(
                    collection_name=self.col.name,
                    location_mode='ACTIVE_OBJECT',
                )
            self.assertEqual(result, {"FINISHED"})
            empty = self.col.root_object
            self.assertIsNotNone(empty)
            self.assertAlmostEqual(empty.location.x, 7.0, places=4)
            self.assertAlmostEqual(empty.location.y, 8.0, places=4)
            self.assertAlmostEqual(empty.location.z, 9.0, places=4)
        finally:
            _h.remove_object(obj)

    def test_center_of_selected_mode_places_empty_at_midpoint(self):
        obj1 = _h.make_mesh_object("OpTarget_c1", location=(0.0, 0.0, 0.0))
        obj2 = _h.make_mesh_object("OpTarget_c2", location=(4.0, 0.0, 0.0))
        self.col.objects.link(obj1)
        self.col.objects.link(obj2)
        try:
            with bpy.context.temp_override(
                selected_objects=[obj1, obj2], active_object=obj1
            ):
                result = bpy.ops.object.create_root_empty(
                    collection_name=self.col.name,
                    location_mode='CENTER_OF_SELECTED',
                )
            self.assertEqual(result, {"FINISHED"})
            empty = self.col.root_object
            self.assertIsNotNone(empty)
            # midpoint of (0,0,0) and (4,0,0) is (2,0,0)
            self.assertAlmostEqual(empty.location.x, 2.0, places=4)
        finally:
            _h.remove_object(obj1)
            _h.remove_object(obj2)

    def test_operator_accessible_via_bpy_ops(self):
        self.assertTrue(hasattr(bpy.ops.object, "create_root_empty"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
