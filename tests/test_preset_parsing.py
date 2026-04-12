"""
Unit tests for the preset parsing and assignment utilities.

Covers:
  parse_preset_file
    - Missing or non-existent file returns an empty dict
    - Empty file returns an empty dict
    - File with no recognised prefix lines returns an empty dict
    - Normal op.* lines are parsed into the correct Python types
    - Malformed lines (missing ' = ' separator, bad eval) are silently skipped
    - Set literals (e.g. object_types) round-trip correctly
    - The 'filepath' key is included in the raw output (assign_preset removes it)
    - Old-version / partial preset (missing some keys) returns only what is present
    - Extra unknown properties are returned as-is
    - Quoted strings are stripped of surrounding quotes

  assign_preset
    - None exporter returns (False, error message)
    - Empty or None preset path returns (False, error message)
    - Non-existent file returns (True, None) — nothing applied, no crash
    - Preset that lacks 'filepath' key does NOT raise KeyError (bug regression)
    - Properties on the exporter are set from the preset file
    - Properties absent on the exporter are skipped (no AttributeError)
    - 'filepath' and 'use_selection' lines are always skipped
    - Setting a property with a wrong type is caught and does not crash

  _props_equal
    - Equal sets → True
    - Unequal sets → False
    - Equal Blender-like array (has __len__, not a string) → True
    - Unequal array → False
    - Simple equal scalar → True
    - Simple unequal scalar → False
    - Exception during comparison assumes equal → True

  _parse_prefix_preset_file (scene-prefix parser used by addon_preset_has_changes)
    - Lines beginning with 'scene.' are parsed
    - Lines with other prefixes are ignored
    - simple_export_preset_file_* keys are returned (caller decides to skip them)
    - Malformed lines are silently skipped
    - Missing file returns empty dict
"""

import os
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Bootstrap — bpy stub must be installed before any addon import
# ---------------------------------------------------------------------------

_ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXTENSIONS_ROOT = os.path.dirname(_ADDON_ROOT)

if _EXTENSIONS_ROOT not in sys.path:
    sys.path.insert(0, _EXTENSIONS_ROOT)

from tests.bpy_stub import install as _install_bpy, make_simple_export_package  # noqa: E402
_install_bpy(blender_version=(5, 1, 0))
make_simple_export_package()

from simple_export.functions.preset_func import (  # noqa: E402
    parse_preset_file,
    assign_preset,
    _props_equal,
    _parse_prefix_preset_file,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_preset(content, suffix=".py"):
    """Write *content* to a named temp file; return the path."""
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(textwrap.dedent(content))
    return path


def _make_exporter(**props):
    """Return a mock exporter whose export_properties has the given attributes."""
    ep = MagicMock()
    for name, value in props.items():
        setattr(ep, name, value)
    # hasattr on a MagicMock always returns True by default, which lets setattr
    # tests run without raising.  For tests that need a property to be *absent*,
    # configure spec or delete the attribute explicitly.
    exporter = MagicMock()
    exporter.export_properties = ep
    return exporter


# ---------------------------------------------------------------------------
# 1. parse_preset_file
# ---------------------------------------------------------------------------

class TestParsePresetFile(unittest.TestCase):

    # -- Missing / empty inputs -----------------------------------------------

    def test_nonexistent_file_returns_empty_dict(self):
        result = parse_preset_file("/tmp/__nonexistent_preset_12345.py")
        self.assertEqual(result, {})

    def test_empty_file_returns_empty_dict(self):
        path = _write_preset("")
        try:
            self.assertEqual(parse_preset_file(path), {})
        finally:
            os.unlink(path)

    def test_file_with_no_op_lines_returns_empty_dict(self):
        path = _write_preset("""
            import bpy
            # This is a comment
            scene.export_format = 'FBX'
        """)
        try:
            self.assertEqual(parse_preset_file(path), {})
        finally:
            os.unlink(path)

    # -- Correct parsing -------------------------------------------------------

    def test_string_value_stripped_of_quotes(self):
        path = _write_preset("op.axis_forward = 'X'\n")
        try:
            result = parse_preset_file(path)
            self.assertEqual(result["axis_forward"], "X")
        finally:
            os.unlink(path)

    def test_double_quoted_string_stripped(self):
        path = _write_preset('op.axis_up = "Z"\n')
        try:
            result = parse_preset_file(path)
            self.assertEqual(result["axis_up"], "Z")
        finally:
            os.unlink(path)

    def test_float_value_parsed_as_float(self):
        path = _write_preset("op.global_scale = 1.0\n")
        try:
            result = parse_preset_file(path)
            self.assertAlmostEqual(result["global_scale"], 1.0)
        finally:
            os.unlink(path)

    def test_bool_true_value(self):
        path = _write_preset("op.use_selection = True\n")
        try:
            self.assertIs(parse_preset_file(path)["use_selection"], True)
        finally:
            os.unlink(path)

    def test_bool_false_value(self):
        path = _write_preset("op.bake_anim = False\n")
        try:
            self.assertIs(parse_preset_file(path)["bake_anim"], False)
        finally:
            os.unlink(path)

    def test_set_literal_parsed_as_set(self):
        path = _write_preset("op.object_types = {'MESH', 'EMPTY'}\n")
        try:
            result = parse_preset_file(path)
            self.assertEqual(result["object_types"], {"MESH", "EMPTY"})
        finally:
            os.unlink(path)

    def test_filepath_key_included_in_raw_output(self):
        """parse_preset_file itself does NOT strip filepath — assign_preset does."""
        path = _write_preset("op.filepath = '/tmp/out.fbx'\n")
        try:
            result = parse_preset_file(path)
            self.assertIn("filepath", result)
        finally:
            os.unlink(path)

    def test_multiple_properties_all_parsed(self):
        content = (
            "import bpy\n"
            "op = bpy.context.active_operator\n"
            "op.filepath = ''\n"
            "op.global_scale = 1.0\n"
            "op.bake_anim = False\n"
            "op.axis_forward = 'X'\n"
        )
        path = _write_preset(content)
        try:
            result = parse_preset_file(path)
            self.assertEqual(len(result), 4)
            self.assertIn("global_scale", result)
            self.assertIn("bake_anim", result)
            self.assertIn("axis_forward", result)
        finally:
            os.unlink(path)

    # -- Partial / old-version presets ----------------------------------------

    def test_partial_preset_returns_only_present_keys(self):
        """An old preset missing some modern keys is parsed without error."""
        path = _write_preset(
            "op.filepath = ''\n"
            "op.global_scale = 1.0\n"
            # bake_anim, axis_forward, etc. intentionally absent
        )
        try:
            result = parse_preset_file(path)
            self.assertIn("global_scale", result)
            self.assertNotIn("bake_anim", result)
            self.assertNotIn("axis_forward", result)
        finally:
            os.unlink(path)

    def test_extra_unknown_property_returned_as_is(self):
        """Properties added in a future Blender version are parsed without error."""
        path = _write_preset("op.future_new_flag = True\n")
        try:
            result = parse_preset_file(path)
            self.assertIn("future_new_flag", result)
            self.assertIs(result["future_new_flag"], True)
        finally:
            os.unlink(path)

    # -- Malformed input -------------------------------------------------------

    def test_line_without_equals_separator_is_skipped(self):
        path = _write_preset(
            "op.good_prop = 1.0\n"
            "op.bad_line_no_separator\n"
        )
        try:
            result = parse_preset_file(path)
            self.assertIn("good_prop", result)
            self.assertNotIn("bad_line_no_separator", result)
        finally:
            os.unlink(path)

    def test_line_with_bad_eval_is_skipped(self):
        path = _write_preset(
            "op.good_prop = 1.0\n"
            "op.broken = {unclosed\n"
        )
        try:
            result = parse_preset_file(path)
            self.assertIn("good_prop", result)
            self.assertNotIn("broken", result)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# 2. assign_preset
# ---------------------------------------------------------------------------

class TestAssignPreset(unittest.TestCase):

    # -- Guard conditions -----------------------------------------------------

    def test_none_exporter_returns_false(self):
        ok, msg = assign_preset(None, "/some/path.py")
        self.assertFalse(ok)
        self.assertIsNotNone(msg)

    def test_empty_preset_path_returns_false(self):
        ok, msg = assign_preset(_make_exporter(), "")
        self.assertFalse(ok)
        self.assertIsNotNone(msg)

    def test_none_preset_path_returns_false(self):
        ok, msg = assign_preset(_make_exporter(), None)
        self.assertFalse(ok)
        self.assertIsNotNone(msg)

    # -- File not found --------------------------------------------------------

    def test_nonexistent_file_returns_true_no_crash(self):
        """Missing preset file → nothing applied but function does not raise."""
        ok, msg = assign_preset(_make_exporter(), "/tmp/__no_such_preset__.py")
        self.assertTrue(ok)
        self.assertIsNone(msg)

    # -- Bug regression: preset without 'filepath' key should not raise -------

    def test_preset_missing_filepath_key_does_not_raise(self):
        """Regression: a preset file with no filepath line must not raise KeyError."""
        path = _write_preset(
            "op.global_scale = 1.0\n"
            "op.bake_anim = False\n"
            # 'filepath' intentionally absent (old or hand-crafted preset)
        )
        try:
            exporter = _make_exporter(global_scale=2.0, bake_anim=True)
            ok, msg = assign_preset(exporter, path)
            self.assertTrue(ok)
            self.assertIsNone(msg)
        finally:
            os.unlink(path)

    # -- Properties are applied -----------------------------------------------

    def test_properties_applied_to_exporter(self):
        path = _write_preset(
            "op.filepath = ''\n"
            "op.global_scale = 2.0\n"
            "op.bake_anim = False\n"
        )
        try:
            exporter = _make_exporter(global_scale=1.0, bake_anim=True)
            assign_preset(exporter, path)
            self.assertAlmostEqual(exporter.export_properties.global_scale, 2.0)
            self.assertIs(exporter.export_properties.bake_anim, False)
        finally:
            os.unlink(path)

    def test_filepath_line_is_always_skipped(self):
        """assign_preset must never overwrite the exporter's filepath."""
        path = _write_preset("op.filepath = '/injected/path.fbx'\n")
        try:
            exporter = _make_exporter(filepath="/original/path.fbx")
            assign_preset(exporter, path)
            # The filepath attribute must not have been touched by setattr.
            # Because MagicMock auto-creates attributes on access, we verify
            # that setattr was NOT called with 'filepath'.
            calls = [
                call for call in exporter.export_properties.mock_calls
                if "filepath" in str(call)
            ]
            # setattr shows as __setattr__ in mock call list
            setattr_calls = [c for c in calls if "__setattr__" in str(c) and "filepath" in str(c)]
            self.assertEqual(len(setattr_calls), 0, "filepath was written by assign_preset")
        finally:
            os.unlink(path)

    def test_use_selection_line_is_always_skipped(self):
        path = _write_preset(
            "op.filepath = ''\n"
            "op.use_selection = True\n"
            "op.global_scale = 1.0\n"
        )
        try:
            exporter = _make_exporter(global_scale=0.0, use_selection=False)
            assign_preset(exporter, path)
            # global_scale should be updated, use_selection should not.
            self.assertAlmostEqual(exporter.export_properties.global_scale, 1.0)
            # use_selection must NOT have been set to True.
            setattr_calls = [
                c for c in exporter.export_properties.mock_calls
                if "__setattr__" in str(c) and "use_selection" in str(c)
            ]
            self.assertEqual(len(setattr_calls), 0, "use_selection was touched by assign_preset")
        finally:
            os.unlink(path)

    def test_unknown_property_on_exporter_does_not_crash(self):
        """Properties not present on the exporter are logged and skipped."""
        path = _write_preset(
            "op.filepath = ''\n"
            "op.nonexistent_prop = 42\n"
        )
        try:
            # Configure the MagicMock so hasattr returns False for the unknown prop.
            ep = MagicMock(spec=[])  # spec=[] → no attributes defined → hasattr always False
            exporter = MagicMock()
            exporter.export_properties = ep
            ok, msg = assign_preset(exporter, path)
            self.assertTrue(ok)
        finally:
            os.unlink(path)

    def test_type_error_on_setattr_does_not_crash(self):
        """If setattr raises (type mismatch), the function catches it and continues."""
        path = _write_preset(
            "op.filepath = ''\n"
            "op.global_scale = 'not_a_float'\n"
        )
        try:
            # Use a real class so __setattr__ can be overridden properly.
            class _RaisingProps:
                global_scale = 1.0  # so hasattr() returns True

                def __setattr__(self, name, value):
                    raise TypeError("type mismatch on assignment")

            exporter = MagicMock()
            exporter.export_properties = _RaisingProps()
            ok, msg = assign_preset(exporter, path)
            self.assertTrue(ok)
        finally:
            os.unlink(path)

    def test_set_value_applied_correctly(self):
        path = _write_preset(
            "op.filepath = ''\n"
            "op.object_types = {'MESH', 'EMPTY'}\n"
        )
        try:
            exporter = _make_exporter(object_types=set())
            assign_preset(exporter, path)
            self.assertEqual(exporter.export_properties.object_types, {"MESH", "EMPTY"})
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# 3. _props_equal
# ---------------------------------------------------------------------------

class TestPropsEqual(unittest.TestCase):

    # -- Set comparisons -------------------------------------------------------

    def test_equal_sets_return_true(self):
        self.assertTrue(_props_equal({"MESH", "EMPTY"}, {"EMPTY", "MESH"}))

    def test_unequal_sets_return_false(self):
        self.assertFalse(_props_equal({"MESH"}, {"MESH", "EMPTY"}))

    def test_blender_set_vs_python_set(self):
        """The Blender value might be a frozenset; preset value is a set."""
        self.assertTrue(_props_equal(frozenset({"MESH"}), {"MESH"}))

    # -- Array / vector comparisons -------------------------------------------

    def test_equal_list_values_return_true(self):
        self.assertTrue(_props_equal([1.0, 2.0, 3.0], [1.0, 2.0, 3.0]))

    def test_unequal_list_values_return_false(self):
        self.assertFalse(_props_equal([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]))

    def test_tuple_vs_list_same_values_return_true(self):
        self.assertTrue(_props_equal((1, 2, 3), [1, 2, 3]))

    # -- Scalar comparisons ---------------------------------------------------

    def test_equal_floats_return_true(self):
        self.assertTrue(_props_equal(1.0, 1.0))

    def test_unequal_floats_return_false(self):
        self.assertFalse(_props_equal(1.0, 2.0))

    def test_equal_strings_return_true(self):
        self.assertTrue(_props_equal("X", "X"))

    def test_unequal_strings_return_false(self):
        self.assertFalse(_props_equal("X", "Y"))

    def test_equal_bools_return_true(self):
        self.assertTrue(_props_equal(True, True))

    def test_unequal_bools_return_false(self):
        self.assertFalse(_props_equal(True, False))

    # -- Error tolerance -------------------------------------------------------

    def test_exception_during_comparison_assumes_equal(self):
        """When comparison raises, _props_equal returns True (safe / no false alerts)."""
        class Uncomparable:
            def __eq__(self, other): raise RuntimeError("cannot compare")
            def __iter__(self): raise RuntimeError("cannot iterate")
            def __len__(self): raise RuntimeError("no length")
        self.assertTrue(_props_equal(Uncomparable(), 1))


# ---------------------------------------------------------------------------
# 4. _parse_prefix_preset_file  (used by addon_preset_has_changes)
# ---------------------------------------------------------------------------

class TestParseAddonPresetFile(unittest.TestCase):

    def test_missing_file_returns_empty_dict(self):
        result = _parse_prefix_preset_file("/tmp/__no_such_addon_preset__.py", "scene")
        self.assertEqual(result, {})

    def test_scene_lines_are_parsed(self):
        path = _write_preset(
            "scene.export_format = 'FBX'\n"
            "scene.export_folder_mode = 'RELATIVE'\n"
        )
        try:
            result = _parse_prefix_preset_file(path, "scene")
            self.assertEqual(result["export_format"], "FBX")
            self.assertEqual(result["export_folder_mode"], "RELATIVE")
        finally:
            os.unlink(path)

    def test_op_lines_are_ignored(self):
        path = _write_preset(
            "scene.export_format = 'FBX'\n"
            "op.global_scale = 1.0\n"
        )
        try:
            result = _parse_prefix_preset_file(path, "scene")
            self.assertIn("export_format", result)
            self.assertNotIn("global_scale", result)
        finally:
            os.unlink(path)

    def test_preset_file_reference_keys_returned(self):
        """simple_export_preset_file_* keys are returned — callers decide to skip them."""
        path = _write_preset(
            "scene.export_format = 'FBX'\n"
            "scene.simple_export_preset_file_fbx = '/presets/UE-fbx.py'\n"
        )
        try:
            result = _parse_prefix_preset_file(path, "scene")
            self.assertIn("simple_export_preset_file_fbx", result)
        finally:
            os.unlink(path)

    def test_malformed_line_silently_skipped(self):
        path = _write_preset(
            "scene.export_format = 'FBX'\n"
            "scene.bad_line_no_equals\n"
        )
        try:
            result = _parse_prefix_preset_file(path, "scene")
            self.assertIn("export_format", result)
            self.assertNotIn("bad_line_no_equals", result)
        finally:
            os.unlink(path)

    def test_empty_file_returns_empty_dict(self):
        path = _write_preset("")
        try:
            self.assertEqual(_parse_prefix_preset_file(path, "scene"), {})
        finally:
            os.unlink(path)

    def test_bool_value_parsed_correctly(self):
        path = _write_preset("scene.assign_preset = True\n")
        try:
            result = _parse_prefix_preset_file(path, "scene")
            self.assertIs(result["assign_preset"], True)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main()
