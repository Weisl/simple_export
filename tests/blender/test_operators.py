"""
Headless Blender tests for Simple Export operators.

Run with:
    blender --background --python tests/blender/test_operators.py

These tests register the real operator classes inside Blender and invoke them
through bpy.ops — the same path Blender itself uses.  This exercises the full
execute() logic on real bpy.data.collections and bpy.data.objects.

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
    - show_name is applied, and the scene/prefs style builders map correctly
  discard_unlinked_root_object (helper function)
    - A root object that is not linked to any collection is removed
    - A root object linked to a collection is kept

  Root empty placement for an object that has a parent
    - Export and instance collections put the root empty at the object's world
      position (not its parent-relative .location) and leave the object in place
    - The export collection's instance_offset is the world position too
    - A Single collection (no base object) uses the passed origin, else the world origin

"""

import math
import os
import sys
import types
import unittest
import unittest.mock
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
_setup_mod = None


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


def _load_functions_module(filename):
    import importlib.util as _ilu
    mod_name = f"simple_export.functions.{filename[:-3]}"
    sys.modules.pop(mod_name, None)
    path = os.path.join(_ADDON_ROOT, "functions", filename)
    spec = _ilu.spec_from_file_location(mod_name, path)
    mod = _ilu.module_from_spec(spec)
    mod.__package__ = "simple_export.functions"
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
    global _fix_mod, _offset_mod, _remove_mod, _setup_mod

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
    _setup_mod = _load_functions_module("collections_setup.py")

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

    def test_object_parented_inside_collection_not_reparented(self):
        """An object whose parent is already inside the collection must be skipped."""
        parent_obj = _h.make_mesh_object("InternalParent", location=(0, 0, 0))
        child_obj = _h.make_mesh_object("InternalChild", location=(1, 0, 0))
        self.col.objects.link(parent_obj)
        self.col.objects.link(child_obj)
        child_obj.parent = parent_obj
        try:
            fn = _get_create_root_empty_fn()
            fn(self.col, Vector((0, 0, 0)), objects_to_parent=[child_obj])
            self.assertIs(child_obj.parent, parent_obj,
                          "Object parented to an in-collection object must not be re-parented")
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

    def test_show_name_applied(self):
        fn = _get_create_root_empty_fn()
        empty = fn(self.col, Vector((0, 0, 0)), show_name=True)
        self.assertTrue(empty.show_name)

    def test_show_name_off_by_default(self):
        fn = _get_create_root_empty_fn()
        empty = fn(self.col, Vector((0, 0, 0)))
        self.assertFalse(empty.show_name)


class TestRootEmptyStyleBuilders(unittest.TestCase):
    """scene_root_empty_style / instance_root_empty_style feed create_root_empty_for_collection."""

    def setUp(self):
        self.col = _h.make_collection("RootEmpty_Style_Test")

    def tearDown(self):
        for obj in list(bpy.data.objects):
            if obj.name.endswith("_root"):
                try:
                    bpy.data.objects.remove(obj)
                except Exception:
                    pass
        _h.remove_collection(self.col)

    def test_scene_style_reads_scene_properties(self):
        scene = types.SimpleNamespace(
            root_empty_display_type='ARROWS',
            root_empty_display_size=2.0,
            root_empty_show_name=True,
        )
        self.assertEqual(
            _offset_mod.scene_root_empty_style(scene),
            {'display_type': 'ARROWS', 'display_size': 2.0, 'show_name': True},
        )

    def test_instance_style_reads_instance_preferences_not_export_ones(self):
        prefs = types.SimpleNamespace(
            instance_root_display_type='SPHERE',
            instance_root_display_size=0.5,
            instance_root_show_name=True,
            # Export-side values must be ignored.
            root_empty_display_type='CUBE',
        )
        self.assertEqual(
            _offset_mod.instance_root_empty_style(prefs),
            {'display_type': 'SPHERE', 'display_size': 0.5, 'show_name': True},
        )

    def test_style_can_be_passed_straight_to_the_helper(self):
        style = {'display_type': 'CONE', 'display_size': 3.0, 'show_name': True}
        empty = _offset_mod.create_root_empty_for_collection(
            self.col, Vector((0, 0, 0)), **style)
        self.assertEqual(empty.empty_display_type, 'CONE')
        self.assertAlmostEqual(empty.empty_display_size, 3.0, places=4)
        self.assertTrue(empty.show_name)


# ---------------------------------------------------------------------------
# 6. discard_unlinked_root_object (helper function)
# ---------------------------------------------------------------------------

class TestDiscardUnlinkedRootObject(unittest.TestCase):
    """A root object deleted in the viewport must not count as the collection's root."""

    def setUp(self):
        self.col = _h.make_collection("StaleRoot_Test")

    def tearDown(self):
        for obj in list(bpy.data.objects):
            if obj.name.startswith("StaleRoot_"):
                try:
                    bpy.data.objects.remove(obj)
                except Exception:
                    pass
        _h.remove_collection(self.col)

    def test_root_not_linked_to_any_collection_is_removed(self):
        stale = bpy.data.objects.new("StaleRoot_root", None)
        self.col.root_object = stale
        _setup_mod.discard_unlinked_root_object(self.col)
        self.assertIsNone(self.col.root_object)
        self.assertNotIn("StaleRoot_root", bpy.data.objects.keys())

    def test_root_linked_to_a_collection_is_kept(self):
        root = bpy.data.objects.new("StaleRoot_root", None)
        self.col.objects.link(root)
        self.col.root_object = root
        _setup_mod.discard_unlinked_root_object(self.col)
        self.assertIs(self.col.root_object, root)
        self.assertIn("StaleRoot_root", bpy.data.objects.keys())

    def test_collection_without_root_is_a_noop(self):
        self.col.root_object = None
        _setup_mod.discard_unlinked_root_object(self.col)
        self.assertIsNone(self.col.root_object)


# ---------------------------------------------------------------------------
# 7. Root empty placement for objects that have a parent
# ---------------------------------------------------------------------------

class TestRootEmptyWorldLocation(unittest.TestCase):
    """The root empty is created where the object appears, not at its parent-relative .location."""

    # Child at local (1, 2, 3) under a parent at (5, 5, 5) turned 90 degrees around Z.
    WORLD = (3.0, 6.0, 8.0)

    @classmethod
    def setUpClass(cls):
        cls._offset_funcs = _load_functions_module("collection_offset.py")
        cls._instance_mod = _load_operator_module("create_instance_collection_ops.py")
        cls._added_selected_prop = not hasattr(bpy.types.Collection, "simple_export_selected")
        if cls._added_selected_prop:
            bpy.types.Collection.simple_export_selected = bpy.props.BoolProperty()

    @classmethod
    def tearDownClass(cls):
        if cls._added_selected_prop:
            del bpy.types.Collection.simple_export_selected

    def setUp(self):
        scene = bpy.context.scene
        self.parent = bpy.data.objects.new("WorldLoc_parent", None)
        self.parent.location = (5, 5, 5)
        self.parent.rotation_euler = (0, 0, math.radians(90))
        scene.collection.objects.link(self.parent)
        self.obj = _h.make_mesh_object("WorldLoc_child", location=(1, 2, 3))
        self.obj.parent = self.parent
        bpy.context.view_layer.update()
        self.col = _h.make_collection("WorldLoc_col")
        self.col.objects.link(self.obj)

    def tearDown(self):
        for obj in list(bpy.data.objects):
            if obj.name.startswith("WorldLoc_"):
                bpy.data.objects.remove(obj)
        for col in list(bpy.data.collections):
            if col.name.startswith("WorldLoc_"):
                bpy.data.collections.remove(col)

    def assertVectorAlmostEqual(self, vec, expected):
        for got, want in zip(vec, expected):
            self.assertAlmostEqual(got, want, places=4)

    def root_world_location(self, collection):
        # A new object has no evaluated matrix_world until the depsgraph runs.
        bpy.context.view_layer.update()
        return collection.root_object.matrix_world.translation

    def test_fixture_local_and_world_locations_differ(self):
        self.assertVectorAlmostEqual(self.obj.location, (1.0, 2.0, 3.0))
        self.assertVectorAlmostEqual(self.obj.matrix_world.translation, self.WORLD)

    def test_object_world_location_helper_returns_world_position(self):
        self.assertVectorAlmostEqual(self._offset_funcs.object_world_location(self.obj), self.WORLD)

    def test_object_world_location_helper_returns_a_copy(self):
        loc = self._offset_funcs.object_world_location(self.obj)
        loc.x += 100.0
        self.assertVectorAlmostEqual(self.obj.matrix_world.translation, self.WORLD)

    def _setup_props(self):
        return types.SimpleNamespace(
            collection_color='NONE',
            collection_instance_offset=True,
            create_empty_root=True,
            root_empty_suffix='_root',
            use_root_object=False,
        )

    def test_export_collection_root_empty_is_at_object_world_location(self):
        style = {'display_type': 'PLAIN_AXES', 'display_size': 1.0, 'show_name': False}
        with unittest.mock.patch.object(_offset_mod, "scene_root_empty_style", return_value=style):
            _setup_mod.setup_collection_properties(self._setup_props(), self.col, self.obj)
        self.assertVectorAlmostEqual(self.root_world_location(self.col), self.WORLD)

    def test_export_collection_keeps_object_where_it_was(self):
        style = {'display_type': 'PLAIN_AXES', 'display_size': 1.0, 'show_name': False}
        with unittest.mock.patch.object(_offset_mod, "scene_root_empty_style", return_value=style):
            _setup_mod.setup_collection_properties(self._setup_props(), self.col, self.obj)
        bpy.context.view_layer.update()
        self.assertVectorAlmostEqual(self.obj.matrix_world.translation, self.WORLD)
        self.assertIs(self.obj.parent, self.col.root_object)

    def test_export_collection_instance_offset_is_object_world_location(self):
        with unittest.mock.patch.object(_offset_mod, "scene_root_empty_style",
                                        return_value={'display_type': 'PLAIN_AXES',
                                                      'display_size': 1.0, 'show_name': False}):
            _setup_mod.setup_collection_properties(self._setup_props(), self.col, self.obj)
        self.assertVectorAlmostEqual(self.col.instance_offset, self.WORLD)

    def test_explicit_origin_places_root_empty_when_there_is_no_base_object(self):
        """Single collections have no one base object; the caller passes the selection centre."""
        style = {'display_type': 'PLAIN_AXES', 'display_size': 1.0, 'show_name': False}
        with unittest.mock.patch.object(_offset_mod, "scene_root_empty_style", return_value=style):
            _setup_mod.setup_collection_properties(
                self._setup_props(), self.col, None, origin=Vector((4.0, 5.0, 6.0)))
        self.assertVectorAlmostEqual(self.root_world_location(self.col), (4.0, 5.0, 6.0))
        self.assertVectorAlmostEqual(self.col.instance_offset, (4.0, 5.0, 6.0))

    def test_without_base_object_or_origin_root_empty_is_at_world_origin(self):
        style = {'display_type': 'PLAIN_AXES', 'display_size': 1.0, 'show_name': False}
        with unittest.mock.patch.object(_offset_mod, "scene_root_empty_style", return_value=style):
            _setup_mod.setup_collection_properties(self._setup_props(), self.col, None)
        self.assertVectorAlmostEqual(self.root_world_location(self.col), (0.0, 0.0, 0.0))

    def test_origin_is_read_before_a_stale_root_is_discarded(self):
        """Removing a leftover root empty must not change where the new one is placed."""
        stale = bpy.data.objects.new("WorldLoc_stale_root", None)
        stale.location = (20, 20, 20)
        self.col.root_object = stale
        style = {'display_type': 'PLAIN_AXES', 'display_size': 1.0, 'show_name': False}
        with unittest.mock.patch.object(_offset_mod, "scene_root_empty_style", return_value=style):
            _setup_mod.setup_collection_properties(self._setup_props(), self.col, self.obj)
        self.assertVectorAlmostEqual(self.root_world_location(self.col), self.WORLD)

    def _instance_operator_stub(self):
        return types.SimpleNamespace(
            _resolve_parent=lambda context: bpy.context.scene.collection,
            root_empty_suffix='_root',
            mark_as_asset=False,
            collection_name="WorldLoc_single",
            report=lambda *args, **kwargs: None,
        )

    def _instance_style(self):
        return {'display_type': 'PLAIN_AXES', 'display_size': 1.0, 'show_name': False}

    def test_instance_collection_root_empty_is_at_object_world_location(self):
        op_cls = self._instance_mod.OBJECT_OT_CreateInstanceCollection
        op_cls._create_for_hierarchy(
            self._instance_operator_stub(), bpy.context, self.obj, self._instance_style())
        collection = bpy.data.collections["WorldLoc_child"]
        self.assertVectorAlmostEqual(self.root_world_location(collection), self.WORLD)
        bpy.context.view_layer.update()
        self.assertVectorAlmostEqual(self.obj.matrix_world.translation, self.WORLD)

    def test_single_instance_collection_root_empty_is_at_object_world_location(self):
        op_cls = self._instance_mod.OBJECT_OT_CreateInstanceCollection
        op_cls._create_single(
            self._instance_operator_stub(), bpy.context, [self.obj], [self.obj],
            self._instance_style())
        collection = bpy.data.collections["WorldLoc_single"]
        self.assertVectorAlmostEqual(self.root_world_location(collection), self.WORLD)
        bpy.context.view_layer.update()
        self.assertVectorAlmostEqual(self.obj.matrix_world.translation, self.WORLD)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
