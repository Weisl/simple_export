"""
Unit tests for operator execute() methods.

Because operators inherit from bpy.types.Operator (a MagicMock), we never
instantiate the classes. Instead we call execute() as an unbound method:

    result = SomeOperator.execute(mock_self, mock_context)

This lets us test the actual execute logic without Blender's operator machinery.

Covers:
  - SIMPLEEXPORT_OT_FixExportFilename.execute
  - OBJECT_OT_set_collection_offset_cursor.execute
  - OBJECT_OT_set_collection_offset_object.execute
  - SIMPLEEXPORT_OT_remove_exporters.execute
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

# Pre-stub modules that would trigger metaclass conflicts or pull in the full
# operator package (__init__.py imports all operators, some of which use
# bpy_extras.io_utils.ImportHelper — a MagicMock — as a base class, causing
# a metaclass conflict with regular Python mixins).
#
# Strategy:
#   1. Stub preferences and UI subpackages (prevent deep cascade).
#   2. Stub simple_export.operators itself (prevent __init__.py from loading
#      all operator files).
#   3. Load only the three operator files we actually want to test directly
#      via importlib, registering them in sys.modules manually.
import importlib.util as _ilutil

_STUB_MODULES = [
    "simple_export.preferences",
    "simple_export.preferences.preferenecs",
    "simple_export.preferences.keymap",
    "simple_export.preferences.collection_setup",
    "simple_export.ui",
    "simple_export.ui.export_panels",
    "simple_export.ui.shared_draw",
    "simple_export.ui.result_popups",
    "simple_export.ui.uilist",
    "simple_export.ui.outliner",
    "simple_export.ui.view3d_object_context_menu",
    "simple_export.ui.popup_list",
    "simple_export.ui.ui_helpers",
    # Stub the operators package so __init__.py never runs
    "simple_export.operators",
]
for _mod_name in _STUB_MODULES:
    if _mod_name not in sys.modules:
        sys.modules[_mod_name] = MagicMock(name=_mod_name)


def _load_operator_file(filename):
    """Load a single operator .py file directly, bypassing operators/__init__.py."""
    mod_name = f"simple_export.operators.{filename[:-3]}"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    path = os.path.join(_ADDON_ROOT, "operators", filename)
    spec = _ilutil.spec_from_file_location(mod_name, path)
    mod = _ilutil.module_from_spec(spec)
    mod.__package__ = "simple_export.operators"
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


# Load dependencies in import order.
# shared_properties is imported by fix_filename via a relative import, so it
# must be in sys.modules before fix_filename.py executes.
_load_operator_file("shared_properties.py")
_fix_filename_mod = _load_operator_file("fix_filename.py")
_offset_ops_mod = _load_operator_file("collection_offset_ops.py")
_remove_mod = _load_operator_file("remove_exporters_ops.py")

SIMPLEEXPORT_OT_FixExportFilename = _fix_filename_mod.SIMPLEEXPORT_OT_FixExportFilename
OBJECT_OT_set_collection_offset_cursor = _offset_ops_mod.OBJECT_OT_set_collection_offset_cursor
OBJECT_OT_set_collection_offset_object = _offset_ops_mod.OBJECT_OT_set_collection_offset_object
SIMPLEEXPORT_OT_remove_exporters = _remove_mod.SIMPLEEXPORT_OT_remove_exporters

# Import exporter_funcs module so we can patch remove_all_collection_exporters
# (it is imported late, inside execute(), so we patch it at the source module).
import simple_export.functions.exporter_funcs as _ef


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_context(export_format="FBX", cursor_location=None, active_object=None):
    ctx = MagicMock()
    ctx.scene.export_format = export_format
    ctx.scene.cursor.location.copy.return_value = cursor_location or MagicMock()
    ctx.object = active_object
    return ctx


def _make_collection(name="MyCollection", exporters=None):
    col = MagicMock()
    col.name = name
    col.exporters = exporters if exporters is not None else [MagicMock()]
    return col


# ---------------------------------------------------------------------------
# 1. SIMPLEEXPORT_OT_FixExportFilename
# ---------------------------------------------------------------------------

class TestFixFilename(unittest.TestCase):
    """SIMPLEEXPORT_OT_FixExportFilename.execute updates the exporter filepath."""

    def _make_self(self, collection_name="MyCollection", prefix="", suffix="",
                   blend_prefix=False):
        mock_self = MagicMock()
        mock_self.collection_name = collection_name
        mock_self.filename_prefix = prefix
        mock_self.filename_suffix = suffix
        mock_self.filename_blend_prefix = blend_prefix
        return mock_self

    def _make_exporter(self, filepath="/exports/MyCollection.fbx"):
        exporter = MagicMock()
        exporter.export_properties.filepath = filepath
        return exporter

    def setUp(self):
        self.bpy = sys.modules["bpy"]

    def test_collection_not_found_returns_cancelled(self):
        self.bpy.data.collections.get.return_value = None
        result = SIMPLEEXPORT_OT_FixExportFilename.execute(
            self._make_self(), _make_context()
        )
        self.assertEqual(result, {"CANCELLED"})

    def test_no_exporters_returns_cancelled(self):
        col = _make_collection(exporters=[])
        self.bpy.data.collections.get.return_value = col
        result = SIMPLEEXPORT_OT_FixExportFilename.execute(
            self._make_self(), _make_context()
        )
        self.assertEqual(result, {"CANCELLED"})

    def test_no_matching_exporter_returns_cancelled(self):
        col = _make_collection()
        self.bpy.data.collections.get.return_value = col
        with patch.object(_fix_filename_mod, "find_exporter", return_value=None):
            result = SIMPLEEXPORT_OT_FixExportFilename.execute(
                self._make_self(), _make_context()
            )
        self.assertEqual(result, {"CANCELLED"})

    def test_happy_path_returns_finished(self):
        col = _make_collection()
        self.bpy.data.collections.get.return_value = col
        exporter = self._make_exporter()

        with (
            patch.object(_fix_filename_mod, "find_exporter", return_value=exporter),
            patch.object(_fix_filename_mod, "generate_base_name", return_value="SM_MyCollection"),
        ):
            result = SIMPLEEXPORT_OT_FixExportFilename.execute(
                self._make_self(), _make_context()
            )
        self.assertEqual(result, {"FINISHED"})

    def test_happy_path_updates_filepath(self):
        col = _make_collection()
        self.bpy.data.collections.get.return_value = col
        exporter = self._make_exporter(filepath="/exports/MyCollection.fbx")

        with (
            patch.object(_fix_filename_mod, "find_exporter", return_value=exporter),
            patch.object(_fix_filename_mod, "generate_base_name", return_value="SM_MyCollection"),
        ):
            SIMPLEEXPORT_OT_FixExportFilename.execute(self._make_self(), _make_context())

        self.assertEqual(exporter.export_properties.filepath, "/exports/SM_MyCollection.fbx")

    def test_happy_path_sets_prev_name(self):
        col = _make_collection(name="MyCollection")
        self.bpy.data.collections.get.return_value = col
        exporter = self._make_exporter()

        with (
            patch.object(_fix_filename_mod, "find_exporter", return_value=exporter),
            patch.object(_fix_filename_mod, "generate_base_name", return_value="SM_MyCollection"),
        ):
            SIMPLEEXPORT_OT_FixExportFilename.execute(self._make_self(), _make_context())

        col.__setitem__.assert_called_once_with("prev_name", "MyCollection")

    def test_generate_base_name_called_with_correct_args(self):
        col = _make_collection(name="MyCollection")
        self.bpy.data.collections.get.return_value = col
        exporter = self._make_exporter()

        mock_self = self._make_self(prefix="SM", suffix="LOD0", blend_prefix=False)

        with (
            patch.object(_fix_filename_mod, "find_exporter", return_value=exporter),
            patch.object(_fix_filename_mod, "generate_base_name", return_value="SM_MyCollection_LOD0") as mock_gen,
        ):
            SIMPLEEXPORT_OT_FixExportFilename.execute(mock_self, _make_context())

        mock_gen.assert_called_once_with("MyCollection", "SM", "LOD0", False)


# ---------------------------------------------------------------------------
# 2. OBJECT_OT_set_collection_offset_cursor
# ---------------------------------------------------------------------------

class TestSetCollectionOffsetCursor(unittest.TestCase):
    """OBJECT_OT_set_collection_offset_cursor.execute sets the offset to cursor location."""

    def setUp(self):
        self.bpy = sys.modules["bpy"]
        self.cursor_location = MagicMock(name="cursor_location")
        self.ctx = _make_context(cursor_location=self.cursor_location)

    def _make_self(self, collection_name="Assets"):
        mock_self = MagicMock()
        mock_self.collection_name = collection_name
        return mock_self

    def test_collection_not_found_returns_cancelled(self):
        self.bpy.data.collections.get.return_value = None
        result = OBJECT_OT_set_collection_offset_cursor.execute(
            self._make_self(), self.ctx
        )
        self.assertEqual(result, {"CANCELLED"})

    def test_happy_path_returns_finished(self):
        self.bpy.data.collections.get.return_value = _make_collection()
        with (
            patch.object(_offset_ops_mod, "set_active_layer_Collection"),
            patch.object(_offset_ops_mod, "set_collection_offset"),
        ):
            result = OBJECT_OT_set_collection_offset_cursor.execute(
                self._make_self(), self.ctx
            )
        self.assertEqual(result, {"FINISHED"})

    def test_calls_set_collection_offset_with_cursor_location(self):
        col = _make_collection()
        self.bpy.data.collections.get.return_value = col

        with (
            patch.object(_offset_ops_mod, "set_active_layer_Collection"),
            patch.object(_offset_ops_mod, "set_collection_offset") as mock_offset,
        ):
            OBJECT_OT_set_collection_offset_cursor.execute(self._make_self(), self.ctx)

        mock_offset.assert_called_once_with(col, self.cursor_location)

    def test_cursor_location_is_copied(self):
        """Execute must call .copy() on cursor.location, not pass a live reference."""
        self.bpy.data.collections.get.return_value = _make_collection()

        with (
            patch.object(_offset_ops_mod, "set_active_layer_Collection"),
            patch.object(_offset_ops_mod, "set_collection_offset"),
        ):
            OBJECT_OT_set_collection_offset_cursor.execute(self._make_self(), self.ctx)

        self.ctx.scene.cursor.location.copy.assert_called()


# ---------------------------------------------------------------------------
# 3. OBJECT_OT_set_collection_offset_object
# ---------------------------------------------------------------------------

class TestSetCollectionOffsetObject(unittest.TestCase):
    """OBJECT_OT_set_collection_offset_object.execute sets the offset to an object location."""

    def setUp(self):
        self.bpy = sys.modules["bpy"]

    def _make_self(self, collection_name="Assets"):
        mock_self = MagicMock()
        mock_self.collection_name = collection_name
        return mock_self

    def test_collection_not_found_returns_cancelled(self):
        self.bpy.data.collections.get.return_value = None
        result = OBJECT_OT_set_collection_offset_object.execute(
            self._make_self(), _make_context()
        )
        self.assertEqual(result, {"CANCELLED"})

    def test_no_active_object_returns_cancelled(self):
        self.bpy.data.collections.get.return_value = _make_collection()
        ctx = _make_context(active_object=None)
        with patch.object(_offset_ops_mod, "set_active_layer_Collection"):
            result = OBJECT_OT_set_collection_offset_object.execute(
                self._make_self(), ctx
            )
        self.assertEqual(result, {"CANCELLED"})

    def test_happy_path_returns_finished(self):
        self.bpy.data.collections.get.return_value = _make_collection()
        active_obj = MagicMock()
        ctx = _make_context(active_object=active_obj)

        with (
            patch.object(_offset_ops_mod, "set_active_layer_Collection"),
            patch.object(_offset_ops_mod, "set_collection_offset"),
        ):
            result = OBJECT_OT_set_collection_offset_object.execute(
                self._make_self(), ctx
            )
        self.assertEqual(result, {"FINISHED"})

    def test_calls_set_collection_offset_with_object_location(self):
        col = _make_collection()
        self.bpy.data.collections.get.return_value = col
        obj_location = MagicMock(name="obj_location")
        active_obj = MagicMock()
        active_obj.location.copy.return_value = obj_location
        ctx = _make_context(active_object=active_obj)

        with (
            patch.object(_offset_ops_mod, "set_active_layer_Collection"),
            patch.object(_offset_ops_mod, "set_collection_offset") as mock_offset,
        ):
            OBJECT_OT_set_collection_offset_object.execute(self._make_self(), ctx)

        mock_offset.assert_called_once_with(col, obj_location)

    def test_object_location_is_copied(self):
        """Execute must call .copy() on obj.location, not pass a live reference."""
        self.bpy.data.collections.get.return_value = _make_collection()
        active_obj = MagicMock()
        ctx = _make_context(active_object=active_obj)

        with (
            patch.object(_offset_ops_mod, "set_active_layer_Collection"),
            patch.object(_offset_ops_mod, "set_collection_offset"),
        ):
            OBJECT_OT_set_collection_offset_object.execute(self._make_self(), ctx)

        active_obj.location.copy.assert_called()


# ---------------------------------------------------------------------------
# 4. SIMPLEEXPORT_OT_remove_exporters
# ---------------------------------------------------------------------------

class TestRemoveExporters(unittest.TestCase):
    """SIMPLEEXPORT_OT_remove_exporters.execute delegates to remove_all_collection_exporters."""

    def setUp(self):
        self.bpy = sys.modules["bpy"]
        # Ensure the module reference used by patch.object is the one that
        # execute()'s late import resolves to.  test_lifecycle clears
        # simple_export.* from sys.modules during test execution; re-register
        # _ef so the late 'from ..functions.exporter_funcs import' in execute()
        # retrieves the same object we patched.
        sys.modules["simple_export.functions.exporter_funcs"] = _ef

    def _make_self(self, collection_name="Assets"):
        mock_self = MagicMock()
        mock_self.collection_name = collection_name
        return mock_self

    def _run(self, collection_mock):
        self.bpy.data.collections.get.return_value = collection_mock
        mock_self = self._make_self()
        with patch.object(_ef, "remove_all_collection_exporters") as mock_remove:
            result = SIMPLEEXPORT_OT_remove_exporters.execute(mock_self, MagicMock())
        return result, mock_self, mock_remove, collection_mock

    def test_returns_finished(self):
        result, _, _, _ = self._run(_make_collection())
        self.assertEqual(result, {"FINISHED"})

    def test_delegates_to_remove_all_collection_exporters(self):
        col = _make_collection()
        _, _, mock_remove, _ = self._run(col)
        mock_remove.assert_called_once_with(col)

    def test_report_called(self):
        _, mock_self, _, _ = self._run(_make_collection())
        mock_self.report.assert_called_once()


if __name__ == "__main__":
    unittest.main()
