"""
Headless Blender tests for addon register / unregister lifecycle.

Run with:
    blender --background --python tests/blender/test_lifecycle.py

Unlike the MagicMock lifecycle tests (which verify that __init__.py calls each
submodule stub's register/unregister in the correct order), these tests verify
the *real* effects of registration inside a live Blender session:

  - After register(), the expected operator types are present in bpy.types
  - After register(), bpy.types.Collection carries the addon's custom properties
  - After unregister(), those operators and properties are gone
  - Repeated register/unregister cycles leave Blender in a clean state
  - The load_post / depsgraph handlers are added and removed correctly

Operator availability is checked via bpy.types (the authoritative registry).
bpy.ops namespace attributes are lazily cached and may remain truthy after
unregister_class(), so they are not used for negative (after-unregister) checks.

Blender normalises operator type names from bl_idname:
  "simple_export.fix_export_filename"  → SIMPLE_EXPORT_OT_fix_export_filename
  "simple_export.remove_exporters"     → SIMPLE_EXPORT_OT_remove_exporters
  "object.set_collection_offset_*"     → OBJECT_OT_set_collection_offset_*
"""

import os
import sys
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

import tests.blender._helpers as _h  # noqa: E402

# Import the package once here so that all relative imports inside submodules
# resolve without triggering circular-import problems.
import simple_export  # noqa: E402  (registers nothing — just sets up the package)
from simple_export.operators import (  # noqa: E402
    fix_filename as _fix_mod,
    collection_offset_ops as _offset_mod,
    remove_exporters_ops as _remove_mod,
)
from simple_export.preferences import collection_setup as _cs_mod  # noqa: E402


# ---------------------------------------------------------------------------
# bpy.types name constants (Blender normalises from bl_idname)
# ---------------------------------------------------------------------------

_TYPE_FIX_FILENAME = "SIMPLE_EXPORT_OT_fix_export_filename"
_TYPE_REMOVE_EXPORTERS = "SIMPLE_EXPORT_OT_remove_exporters"
_TYPE_CURSOR_OFFSET = "OBJECT_OT_set_collection_offset_cursor"
_TYPE_OBJECT_OFFSET = "OBJECT_OT_set_collection_offset_object"


def _in_bpy_types(name):
    """Return True when the named type exists in bpy.types."""
    return hasattr(bpy.types, name)


# ---------------------------------------------------------------------------
# 1. preferences.collection_setup register / unregister
# ---------------------------------------------------------------------------

class TestCollectionSetupLifecycle(unittest.TestCase):
    """register() adds Collection properties and handlers; unregister() removes them."""

    def setUp(self):
        # Each test starts with the module unregistered.
        pass

    def tearDown(self):
        # Ensure cleanup even if the test body raised.
        try:
            _cs_mod.unregister()
        except Exception:
            pass

    # -- Properties appear after register() --

    def test_pre_export_ops_present_after_register(self):
        _cs_mod.register()
        self.assertTrue(hasattr(bpy.types.Collection, "pre_export_ops"))

    def test_use_root_object_present_after_register(self):
        _cs_mod.register()
        self.assertTrue(hasattr(bpy.types.Collection, "use_root_object"))

    def test_simple_export_selected_present_after_register(self):
        _cs_mod.register()
        self.assertTrue(hasattr(bpy.types.Collection, "simple_export_selected"))

    def test_collection_pre_export_ops_class_is_registered(self):
        """CollectionPreExportOps has bl_rna in its __dict__ when registered.

        PropertyGroup types do not appear in dir(bpy.types) in Blender 5.1, so
        we check registration via the bl_rna sentinel that register_class() adds
        to the class dict.
        """
        from simple_export.preferences.collection_setup import CollectionPreExportOps
        _cs_mod.register()
        self.assertIn(
            "bl_rna",
            CollectionPreExportOps.__dict__,
            "CollectionPreExportOps does not have bl_rna after register()",
        )

    # -- Properties absent after unregister() --

    def test_pre_export_ops_absent_after_unregister(self):
        _cs_mod.register()
        _cs_mod.unregister()
        self.assertFalse(hasattr(bpy.types.Collection, "pre_export_ops"))

    def test_use_root_object_absent_after_unregister(self):
        _cs_mod.register()
        _cs_mod.unregister()
        self.assertFalse(hasattr(bpy.types.Collection, "use_root_object"))

    def test_collection_pre_export_ops_class_is_unregistered_after_unregister(self):
        """bl_rna is removed from CollectionPreExportOps when unregister_class() is called."""
        from simple_export.preferences.collection_setup import CollectionPreExportOps
        _cs_mod.register()
        _cs_mod.unregister()
        self.assertNotIn(
            "bl_rna",
            CollectionPreExportOps.__dict__,
            "CollectionPreExportOps still has bl_rna after unregister()",
        )

    # -- Handlers --

    def test_load_post_handler_added_on_register(self):
        _cs_mod.register()
        from simple_export.preferences.collection_setup import load_post_handler
        self.assertIn(load_post_handler, bpy.app.handlers.load_post)

    def test_load_post_handler_removed_on_unregister(self):
        _cs_mod.register()
        from simple_export.preferences.collection_setup import load_post_handler
        _cs_mod.unregister()
        self.assertNotIn(load_post_handler, bpy.app.handlers.load_post)

    def test_depsgraph_handler_added_on_register(self):
        _cs_mod.register()
        from simple_export.preferences.collection_setup import update_collection_offset
        self.assertIn(update_collection_offset, bpy.app.handlers.depsgraph_update_post)

    def test_depsgraph_handler_removed_on_unregister(self):
        _cs_mod.register()
        from simple_export.preferences.collection_setup import update_collection_offset
        _cs_mod.unregister()
        self.assertNotIn(update_collection_offset, bpy.app.handlers.depsgraph_update_post)

    # -- Robustness --

    def test_register_unregister_cycle_twice(self):
        """Two complete register/unregister cycles must leave Blender clean."""
        for cycle in range(2):
            _cs_mod.register()
            self.assertTrue(
                hasattr(bpy.types.Collection, "pre_export_ops"),
                f"Cycle {cycle + 1}: pre_export_ops missing after register()",
            )
            _cs_mod.unregister()
            self.assertFalse(
                hasattr(bpy.types.Collection, "pre_export_ops"),
                f"Cycle {cycle + 1}: pre_export_ops still present after unregister()",
            )


# ---------------------------------------------------------------------------
# 2. Operator module register / unregister
# ---------------------------------------------------------------------------

class TestOperatorModuleLifecycle(unittest.TestCase):
    """Each operator module's register() adds its type to bpy.types; unregister() removes it."""

    def setUp(self):
        # Guarantee each test starts with all three operator modules unregistered,
        # regardless of what a previous test (or test class) may have left behind.
        for mod in (_fix_mod, _offset_mod, _remove_mod):
            try:
                mod.unregister()
            except Exception:
                pass

    def tearDown(self):
        for mod in (_fix_mod, _offset_mod, _remove_mod):
            try:
                mod.unregister()
            except Exception:
                pass

    # -- fix_filename --

    def test_fix_filename_type_present_after_register(self):
        _fix_mod.register()
        self.assertTrue(
            _in_bpy_types(_TYPE_FIX_FILENAME),
            f"{_TYPE_FIX_FILENAME} not in bpy.types after register()",
        )

    def test_fix_filename_type_absent_after_unregister(self):
        _fix_mod.register()
        _fix_mod.unregister()
        self.assertFalse(_in_bpy_types(_TYPE_FIX_FILENAME))

    def test_fix_filename_accessible_via_bpy_ops(self):
        _fix_mod.register()
        self.assertTrue(hasattr(bpy.ops.simple_export, "fix_export_filename"))

    # -- collection_offset_ops --

    def test_cursor_offset_type_present_after_register(self):
        _offset_mod.register()
        self.assertTrue(_in_bpy_types(_TYPE_CURSOR_OFFSET))

    def test_object_offset_type_present_after_register(self):
        _offset_mod.register()
        self.assertTrue(_in_bpy_types(_TYPE_OBJECT_OFFSET))

    def test_offset_types_absent_after_unregister(self):
        _offset_mod.register()
        _offset_mod.unregister()
        self.assertFalse(_in_bpy_types(_TYPE_CURSOR_OFFSET))
        self.assertFalse(_in_bpy_types(_TYPE_OBJECT_OFFSET))

    # -- remove_exporters_ops --

    def test_remove_exporters_type_present_after_register(self):
        _remove_mod.register()
        self.assertTrue(_in_bpy_types(_TYPE_REMOVE_EXPORTERS))

    def test_remove_exporters_type_absent_after_unregister(self):
        _remove_mod.register()
        _remove_mod.unregister()
        self.assertFalse(_in_bpy_types(_TYPE_REMOVE_EXPORTERS))

    def test_remove_exporters_accessible_via_bpy_ops(self):
        _remove_mod.register()
        self.assertTrue(hasattr(bpy.ops.simple_export, "remove_exporters"))


# ---------------------------------------------------------------------------
# 3. New collection carries the properties immediately after registration
# ---------------------------------------------------------------------------

class TestNewCollectionHasProperties(unittest.TestCase):
    """A collection created after register() must carry the addon's properties."""

    def setUp(self):
        _cs_mod.register()

    def tearDown(self):
        try:
            _cs_mod.unregister()
        except Exception:
            pass

    def test_new_collection_has_pre_export_ops(self):
        col = _h.make_collection("NewCol_Props")
        try:
            self.assertTrue(hasattr(col, "pre_export_ops"))
        finally:
            _h.remove_collection(col)

    def test_new_collection_has_correct_bool_defaults(self):
        col = _h.make_collection("NewCol_Defaults")
        try:
            self.assertTrue(col.pre_export_ops.triangulate_keep_normals)
            self.assertFalse(col.pre_export_ops.move_by_collection_offset)
            self.assertFalse(col.pre_export_ops.triangulate_before_export)
        finally:
            _h.remove_collection(col)

    def test_new_collection_has_use_root_object(self):
        col = _h.make_collection("NewCol_RootObj")
        try:
            self.assertTrue(hasattr(col, "use_root_object"))
        finally:
            _h.remove_collection(col)


# ---------------------------------------------------------------------------
# 4. Full addon smoke test (may skip if UI classes fail in background mode)
# ---------------------------------------------------------------------------

class TestFullAddonSmoke(unittest.TestCase):
    """Attempt a complete register() / unregister() of the addon.

    UI panel classes typically require an Area/Region and may not register in
    background mode — this test skips gracefully when that happens.
    """

    def test_full_register_unregister(self):
        try:
            simple_export.register()
        except Exception as exc:
            self.skipTest(f"Full addon register() failed in background mode: {exc}")

        try:
            self.assertTrue(
                hasattr(bpy.types.Collection, "pre_export_ops"),
                "pre_export_ops missing after full register()",
            )
            self.assertTrue(
                _in_bpy_types(_TYPE_FIX_FILENAME),
                f"{_TYPE_FIX_FILENAME} missing after full register()",
            )
        finally:
            try:
                simple_export.unregister()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
