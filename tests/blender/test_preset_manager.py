"""
Headless Blender tests for the preset manager in the addon preferences.

Run with:
    blender --background --factory-startup --python tests/blender/test_preset_manager.py

The Presets tab of the preferences edits preset files through the preferences' own
copy of the preset properties (the "editor"). These tests pin down the rules:

  - Selecting a preset for editing loads it into the editor and never touches the
    scene or the preset chosen in the N panel; applying a preset never touches the editor
  - Update overwrites a user preset, but built-in (locked) presets are refused
  - Save as New / Duplicate never overwrite an existing or built-in preset
  - Every built-in preset survives editor -> file unchanged (Update rewrites the whole file)
  - Built-in preset files are rewritten from the addon on startup, user presets are left alone
"""

import os
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import bpy

_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_TESTS_DIR = os.path.dirname(_FILE_DIR)
_ADDON_ROOT = os.path.dirname(_TESTS_DIR)
_EXTENSIONS_ROOT = os.path.dirname(_ADDON_ROOT)
if _EXTENSIONS_ROOT not in sys.path:
    sys.path.insert(0, _EXTENSIONS_ROOT)
if _ADDON_ROOT not in sys.path:
    sys.path.insert(0, _ADDON_ROOT)

import simple_export  # noqa: E402,F401  (sets up the package for relative imports)
from simple_export.functions.preset_func import parse_addon_preset_file  # noqa: E402
from simple_export.preferences import preferenecs  # noqa: E402
from simple_export.presets_addon import (  # noqa: E402
    _render_addon_preset, create_addon_preset_files,
)
from simple_export.presets_addon import exporter_preset  # noqa: E402
from simple_export.presets_addon.preset_data_exporters import presets_simple_exporter  # noqa: E402

_BUILTIN = "Unity-default"
_OTHER_BUILTIN = "UE-default"


def _values_equal(a, b):
    if isinstance(a, (list, tuple)) or isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_values_equal(x, y) for x, y in zip(a, b))
    if isinstance(a, float) or isinstance(b, float):
        return abs(a - b) < 1e-5
    return a == b


class PresetManagerTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bpy.utils.register_class(preferenecs.SIMPLE_EXPORT_preferences)
        if "simple_export" not in bpy.context.preferences.addons:
            entry = bpy.context.preferences.addons.new()
            entry.module = "simple_export"
        # Scene properties that presets write to (created from the preferences' defaults).
        preferenecs.initialize_properties_collection_generation()
        preferenecs.initialize_properties_file_path()
        preferenecs.initialize_format_specific_properties()
        bpy.types.Scene.simple_export_selected_preset = bpy.props.StringProperty(default="")
        exporter_preset.register()

    @classmethod
    def tearDownClass(cls):
        exporter_preset.unregister()
        del bpy.types.Scene.simple_export_selected_preset
        entry = bpy.context.preferences.addons.get("simple_export")
        if entry:
            bpy.context.preferences.addons.remove(entry)
        bpy.utils.unregister_class(preferenecs.SIMPLE_EXPORT_preferences)

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.folder = self._tmp.name
        patcher = patch.object(exporter_preset, "simple_export_presets_folder", return_value=self.folder)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

        create_addon_preset_files(presets_simple_exporter, self.folder)
        self.prefs = bpy.context.preferences.addons["simple_export"].preferences
        self.wm = bpy.context.window_manager
        self.scene = bpy.context.scene
        self.wm.simple_export_editing_preset = ""
        self.scene.simple_export_selected_preset = ""

    def path(self, name):
        return os.path.join(self.folder, f"{name}.py")

    def select(self, name):
        result = bpy.ops.simple_export.select_preset_for_editing(filepath=self.path(name))
        self.assertEqual(result, {'FINISHED'})

    def duplicate(self, source, new_name):
        self.select(source)
        return bpy.ops.simple_export.duplicate_preset('EXEC_DEFAULT', name=new_name, source_path=self.path(source))


class TestSelectingAndApplyingAreSeparate(PresetManagerTestCase):
    def test_select_loads_values_into_editor(self):
        expected = presets_simple_exporter[_BUILTIN]
        self.prefs.export_format = 'OBJ' if expected["export_format"] != 'OBJ' else 'FBX'
        self.select(_BUILTIN)
        self.assertEqual(self.prefs.export_format, expected["export_format"])
        self.assertEqual(self.wm.simple_export_editing_preset, self.path(_BUILTIN))

    def test_select_does_not_touch_scene_or_n_panel_selection(self):
        other = self.path(_OTHER_BUILTIN)
        self.scene.simple_export_selected_preset = other
        self.scene.filename_prefix = "scene-value"
        self.scene.export_format = 'OBJ'

        self.select(_BUILTIN)

        self.assertEqual(self.scene.simple_export_selected_preset, other)
        self.assertEqual(self.scene.filename_prefix, "scene-value")
        self.assertEqual(self.scene.export_format, 'OBJ')

    def test_select_resets_properties_the_preset_does_not_define(self):
        self.prefs.filename_suffix = "left-over"
        with open(self.path("sparse"), "w") as f:
            f.write("import bpy\nscene = bpy.context.scene\nscene.filename_prefix = 'only-this'\n")
        bpy.ops.simple_export.select_preset_for_editing(filepath=self.path("sparse"))
        self.assertEqual(self.prefs.filename_prefix, "only-this")
        self.assertEqual(self.prefs.filename_suffix, self.prefs.bl_rna.properties["filename_suffix"].default)

    def test_apply_changes_scene_but_not_editor(self):
        # A small preset: the built-ins also set per-format Scene properties that only the
        # fully registered addon provides.
        with open(self.path("applied"), "w") as f:
            f.write("import bpy\nscene = bpy.context.scene\nscene.filename_prefix = 'from-preset'\n")
        self.prefs.filename_prefix = "editor-value"
        self.scene.filename_prefix = "scene-value"

        result = bpy.ops.simple_export.apply_preset(
            filepath=self.path("applied"), menu_idname=exporter_preset.EXPORT_MT_scene_presets.__name__)

        self.assertEqual(result, {'FINISHED'})
        self.assertEqual(self.scene.simple_export_selected_preset, self.path("applied"))
        self.assertEqual(self.scene.filename_prefix, "from-preset")
        self.assertEqual(self.prefs.filename_prefix, "editor-value")
        self.assertEqual(self.wm.simple_export_editing_preset, "")


class TestEditingUserPresets(PresetManagerTestCase):
    def test_duplicate_copies_selects_copy_and_leaves_source_untouched(self):
        original = open(self.path(_BUILTIN)).read()
        self.scene.simple_export_selected_preset = "n-panel-choice"

        self.assertEqual(self.duplicate(_BUILTIN, "My Copy"), {'FINISHED'})

        self.assertTrue(os.path.isfile(self.path("My_Copy")))
        self.assertEqual(self.wm.simple_export_editing_preset, self.path("My_Copy"))
        self.assertEqual(open(self.path(_BUILTIN)).read(), original)
        self.assertEqual(self.scene.simple_export_selected_preset, "n-panel-choice")

    def test_update_overwrites_the_selected_user_preset(self):
        self.duplicate(_BUILTIN, "Mine")
        self.prefs.filename_prefix = "changed-in-editor"

        self.assertEqual(bpy.ops.simple_export.update_preset('EXEC_DEFAULT'), {'FINISHED'})

        self.assertEqual(parse_addon_preset_file(self.path("Mine"))["filename_prefix"], "changed-in-editor")

    def test_update_does_not_touch_other_presets(self):
        self.duplicate(_BUILTIN, "Mine")
        untouched = open(self.path(_BUILTIN)).read()
        self.prefs.filename_prefix = "changed-in-editor"
        bpy.ops.simple_export.update_preset('EXEC_DEFAULT')
        self.assertEqual(open(self.path(_BUILTIN)).read(), untouched)

    def test_save_as_new_writes_editor_values_and_selects_the_new_preset(self):
        self.prefs.filename_prefix = "brand-new"
        result = bpy.ops.simple_export.save_preset_from_preferences('EXEC_DEFAULT', name="Brand New")
        self.assertEqual(result, {'FINISHED'})
        self.assertEqual(parse_addon_preset_file(self.path("Brand_New"))["filename_prefix"], "brand-new")
        self.assertEqual(self.wm.simple_export_editing_preset, self.path("Brand_New"))

    def test_remove_deletes_user_preset_and_clears_selections(self):
        self.duplicate(_BUILTIN, "Doomed")
        self.scene.simple_export_selected_preset = self.path("Doomed")

        self.assertEqual(bpy.ops.simple_export.remove_preset('EXEC_DEFAULT'), {'FINISHED'})

        self.assertFalse(os.path.exists(self.path("Doomed")))
        self.assertEqual(self.wm.simple_export_editing_preset, "")
        self.assertEqual(self.scene.simple_export_selected_preset, "")


class TestBuiltinPresetsAreLocked(PresetManagerTestCase):
    def test_update_and_remove_are_unavailable_for_a_builtin(self):
        self.select(_BUILTIN)
        self.assertFalse(bpy.ops.simple_export.update_preset.poll())
        self.assertFalse(bpy.ops.simple_export.remove_preset.poll())

    def test_update_and_remove_are_unavailable_without_a_selection(self):
        self.assertFalse(bpy.ops.simple_export.update_preset.poll())
        self.assertFalse(bpy.ops.simple_export.remove_preset.poll())
        self.assertFalse(bpy.ops.simple_export.duplicate_preset.poll())

    def test_builtin_file_is_unchanged_after_failed_update_attempt(self):
        original = open(self.path(_BUILTIN)).read()
        self.select(_BUILTIN)
        self.prefs.filename_prefix = "should-not-be-saved"
        with self.assertRaises(RuntimeError):
            bpy.ops.simple_export.update_preset('EXEC_DEFAULT')
        self.assertEqual(open(self.path(_BUILTIN)).read(), original)

    def test_save_as_new_refuses_a_builtin_name(self):
        original = open(self.path(_BUILTIN)).read()
        result = bpy.ops.simple_export.save_preset_from_preferences('EXEC_DEFAULT', name=_BUILTIN)
        self.assertEqual(result, {'CANCELLED'})
        self.assertEqual(open(self.path(_BUILTIN)).read(), original)

    def test_save_as_new_refuses_an_existing_user_preset(self):
        self.duplicate(_BUILTIN, "Taken")
        before = open(self.path("Taken")).read()
        self.prefs.filename_prefix = "would-overwrite"
        result = bpy.ops.simple_export.save_preset_from_preferences('EXEC_DEFAULT', name="Taken")
        self.assertEqual(result, {'CANCELLED'})
        self.assertEqual(open(self.path("Taken")).read(), before)

    def test_duplicate_refuses_an_existing_name(self):
        self.duplicate(_BUILTIN, "Taken")
        self.assertEqual(self.duplicate(_OTHER_BUILTIN, "Taken"), {'CANCELLED'})

    def test_names_with_path_separators_are_rejected(self):
        result = bpy.ops.simple_export.save_preset_from_preferences('EXEC_DEFAULT', name="../escape")
        self.assertEqual(result, {'CANCELLED'})
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.folder), "escape.py")))


class TestEditorRoundTrip(PresetManagerTestCase):
    """Update rewrites the whole preset file from the editor, so nothing may be lost or altered."""

    def test_every_builtin_survives_select_then_write(self):
        problems = []
        for name in presets_simple_exporter:
            self.select(name)
            copy_path = self.path(f"roundtrip-{name}")
            exporter_preset.write_preset_from_editor(self.prefs, copy_path)
            original = parse_addon_preset_file(self.path(name))
            written = parse_addon_preset_file(copy_path)
            for prop, value in original.items():
                if prop not in written:
                    problems.append(f"{name}: '{prop}' missing after round trip")
                elif not _values_equal(value, written[prop]):
                    problems.append(f"{name}: '{prop}' {value!r} -> {written[prop]!r}")
        self.assertEqual(problems, [])


class TestBuiltinPresetsAreRefreshed(PresetManagerTestCase):
    def test_edited_builtin_is_restored(self):
        shipped = _render_addon_preset(presets_simple_exporter[_BUILTIN])
        with open(self.path(_BUILTIN), "w") as f:
            f.write("scene.filename_prefix = 'hand-edited'\n")
        create_addon_preset_files(presets_simple_exporter, self.folder)
        self.assertEqual(open(self.path(_BUILTIN)).read(), shipped)

    def test_outdated_builtin_from_an_older_addon_version_is_replaced(self):
        # Simulate an install written by an older addon version: same name, different content.
        with open(self.path(_BUILTIN), "w") as f:
            f.write(_render_addon_preset({**presets_simple_exporter[_BUILTIN], "filename_prefix": "old-version"}))
        create_addon_preset_files(presets_simple_exporter, self.folder)
        self.assertNotEqual(parse_addon_preset_file(self.path(_BUILTIN)).get("filename_prefix"), "old-version")

    def test_deleted_builtin_is_recreated(self):
        os.remove(self.path(_BUILTIN))
        create_addon_preset_files(presets_simple_exporter, self.folder)
        self.assertTrue(os.path.isfile(self.path(_BUILTIN)))

    def test_user_presets_are_left_alone(self):
        self.duplicate(_BUILTIN, "Mine")
        with open(self.path("Mine"), "a") as f:
            f.write("scene.filename_prefix = 'user-edit'\n")
        before = open(self.path("Mine")).read()
        create_addon_preset_files(presets_simple_exporter, self.folder)
        self.assertEqual(open(self.path("Mine")).read(), before)

    def test_unchanged_builtin_is_not_rewritten(self):
        path = self.path(_BUILTIN)
        os.utime(path, (1_000_000_000, 1_000_000_000))
        create_addon_preset_files(presets_simple_exporter, self.folder)
        self.assertEqual(int(os.path.getmtime(path)), 1_000_000_000)


class _RecordingLayout:
    """Headless Blender has no UI region, so there is no real UILayout to draw into. This one
    records every call made on it (and on the layouts it hands back) as (name, text) pairs in
    `calls`, e.g. ("box().row.operator", "box().row.operator('simple_export.duplicate_preset')").
    `drawn` is all the call texts joined, for asserting on what the draw code offers."""

    def __init__(self, calls=None, path=""):
        self.calls = [] if calls is None else calls
        self._path = path

    @property
    def drawn(self):
        return "\n".join(text for _name, text in self.calls)

    def __getattr__(self, attr):
        if attr.startswith("__"):
            raise AttributeError(attr)
        name = f"{self._path}.{attr}" if self._path else attr

        def record(*args, **kwargs):
            shown = [repr(arg) for arg in args] + [f"{key}={value!r}" for key, value in kwargs.items()]
            self.calls.append((name, f"{name}({', '.join(shown)})"))
            child = _RecordingLayout(self.calls, f"{name}()")
            return (child, child) if attr == "panel" else child  # panel() is unpacked to (header, body)
        return record


class _PrefsProxy:
    """Stands in for `self` in AddonPreferences.draw: the real preferences, but with a fake layout."""

    def __init__(self, prefs, layout):
        self._prefs = prefs
        self.layout = layout

    def __getattr__(self, name):
        return getattr(self._prefs, name)


class TestPresetsTabDraws(PresetManagerTestCase):
    """Smoke test for the Presets tab: the draw code can't run in a real UI headless, so it
    runs against a recording fake layout."""

    def _draw(self):
        layout = _RecordingLayout()
        context = SimpleNamespace(
            window_manager=self.wm, scene=self.scene, region=SimpleNamespace(width=400),
            preferences=bpy.context.preferences,
        )
        self.prefs.prefs_tabs = 'SETTINGS'
        with patch.object(preferenecs, "label_multiline"):
            preferenecs.SIMPLE_EXPORT_preferences.draw(_PrefsProxy(self.prefs, layout), context)
        return layout.drawn

    def test_draws_without_a_selection(self):
        drawn = self._draw()
        self.assertIn("No preset selected", drawn)
        self.assertIn("SIMPLE_EXPORT_MT_edit_preset", drawn)  # the one-row picker

    def test_draws_with_a_locked_and_with_a_user_preset_selected(self):
        self.select(_BUILTIN)
        self.assertIn(f"'{_BUILTIN}'", self._draw())
        self.duplicate(_BUILTIN, "Mine")
        self.assertIn("'Mine'", self._draw())

    def test_tab_never_applies_a_preset(self):
        self.select(_BUILTIN)
        drawn = self._draw()
        self.assertNotIn("simple_export.apply_preset", drawn)
        self.assertNotIn("simple_export.set_default_preset", drawn)
        self.assertNotIn("simple_export.scene_preset", drawn)

    def test_picker_entries_select_for_editing_and_never_apply(self):
        context = SimpleNamespace(window_manager=self.wm, scene=self.scene, preferences=bpy.context.preferences)
        drawn_any_preset = False
        for menu in exporter_preset.EDIT_PRESET_MENU_CLASSES:
            layout = _RecordingLayout()
            menu.draw(SimpleNamespace(layout=layout), context)
            drawn = layout.drawn
            self.assertNotIn("simple_export.apply_preset", drawn)
            drawn_any_preset = drawn_any_preset or "simple_export.select_preset_for_editing" in drawn
        self.assertTrue(drawn_any_preset)

    def test_picker_lists_only_categories_that_have_presets(self):
        context = SimpleNamespace(window_manager=self.wm, scene=self.scene, preferences=bpy.context.preferences)
        layout = _RecordingLayout()
        exporter_preset.SIMPLE_EXPORT_MT_edit_preset.draw(SimpleNamespace(layout=layout), context)
        drawn = layout.drawn
        self.assertIn("SIMPLE_EXPORT_MT_edit_preset_Godot", drawn)
        self.assertNotIn("SIMPLE_EXPORT_MT_edit_preset_Custom", drawn)  # nothing user-made yet
        self.duplicate(_BUILTIN, "Mine")
        layout = _RecordingLayout()
        exporter_preset.SIMPLE_EXPORT_MT_edit_preset.draw(SimpleNamespace(layout=layout), context)
        self.assertIn("SIMPLE_EXPORT_MT_edit_preset_Custom", layout.drawn)

    def test_toolbar_offers_the_management_operations(self):
        drawn = self._draw()
        for op in ("save_preset_from_preferences", "duplicate_preset", "remove_preset"):
            self.assertIn(f"simple_export.{op}", drawn)

    def test_modified_row_appears_only_with_unsaved_edits(self):
        self.duplicate(_BUILTIN, "Mine")
        clean = self._draw()
        self.assertNotIn("Modified", clean)
        self.assertNotIn("simple_export.update_preset", clean)

        self.prefs.filename_prefix = "edited"
        dirty = self._draw()
        self.assertIn("Modified", dirty)
        self.assertIn("Revert", dirty)
        self.assertIn("simple_export.update_preset", dirty)

    def test_modified_builtin_offers_save_as_copy_instead_of_update(self):
        self.select(_BUILTIN)
        self.prefs.filename_prefix = "edited"
        drawn = self._draw()
        self.assertIn("Modified", drawn)
        self.assertIn("Save as Copy", drawn)
        self.assertNotIn("simple_export.update_preset", drawn)

    def test_settings_are_plain_boxes_without_collapsible_panels(self):
        self.select(_BUILTIN)
        layout = _RecordingLayout()
        from simple_export.ui.shared_draw import draw_full_exporer_settings
        with patch.object(preferenecs, "label_multiline"):  # needs a UI region
            draw_full_exporer_settings(layout, self.prefs)
        self.assertEqual([name for name, _text in layout.calls if name == "panel"], [])
        # format, folder, naming, collection, root object, pre-export
        self.assertEqual(len([name for name, _text in layout.calls if name == "box"]), 6)


class TestEditorChangeTracking(PresetManagerTestCase):
    """The Presets tab shows 'Modified' when the editor differs from the selected preset's file."""

    def changed(self, name):
        return exporter_preset.editor_has_changes(self.prefs, self.path(name))

    def test_a_freshly_selected_preset_is_unmodified(self):
        for name in presets_simple_exporter:
            self.select(name)
            self.assertFalse(self.changed(name), f"{name} reads as modified right after selecting it")

    def test_editing_a_value_marks_modified_and_undoing_the_edit_clears_it(self):
        self.select(_BUILTIN)
        original = self.prefs.filename_prefix
        self.prefs.filename_prefix = "edited"
        self.assertTrue(self.changed(_BUILTIN))
        self.prefs.filename_prefix = original
        self.assertFalse(self.changed(_BUILTIN))

    def test_reselecting_the_same_preset_reverts_the_edits(self):
        self.select(_BUILTIN)
        original = self.prefs.filename_prefix
        self.prefs.filename_prefix = "edited"
        self.select(_BUILTIN)
        self.assertEqual(self.prefs.filename_prefix, original)
        self.assertFalse(self.changed(_BUILTIN))

    def test_update_clears_modified(self):
        self.duplicate(_BUILTIN, "Mine")
        self.prefs.filename_prefix = "edited"
        self.assertTrue(self.changed("Mine"))
        bpy.ops.simple_export.update_preset('EXEC_DEFAULT')
        self.assertFalse(self.changed("Mine"))

    def test_save_as_new_tracks_the_new_preset_as_unmodified(self):
        self.select(_BUILTIN)
        self.prefs.filename_prefix = "edited"
        bpy.ops.simple_export.save_preset_from_preferences('EXEC_DEFAULT', name="Kept Edits")
        self.assertFalse(self.changed("Kept_Edits"))
        self.assertEqual(self.wm.simple_export_editing_preset, self.path("Kept_Edits"))

    def test_the_source_of_a_save_as_copy_is_left_as_it_was(self):
        original = open(self.path(_BUILTIN)).read()
        self.select(_BUILTIN)
        self.prefs.filename_prefix = "edited"
        bpy.ops.simple_export.save_preset_from_preferences('EXEC_DEFAULT', name="Kept Edits")
        self.assertEqual(open(self.path(_BUILTIN)).read(), original)

    def test_a_preset_that_was_never_loaded_is_not_reported_as_modified(self):
        self.prefs.filename_prefix = "edited"
        self.assertFalse(self.changed(_BUILTIN))

    def test_selecting_another_preset_forgets_the_previous_one(self):
        self.select(_BUILTIN)
        self.prefs.filename_prefix = "edited"
        self.select(_OTHER_BUILTIN)
        self.assertFalse(self.changed(_BUILTIN))
        self.assertFalse(self.changed(_OTHER_BUILTIN))


class TestNewPresetNames(PresetManagerTestCase):
    def test_usable_name_gets_a_path(self):
        filepath, problem = exporter_preset._new_preset_filepath("Fresh Name")
        self.assertEqual(problem, "")
        self.assertEqual(filepath, self.path("Fresh_Name"))

    def test_unusable_names_explain_why(self):
        self.duplicate(_BUILTIN, "Taken")
        for name, fragment in (("", "empty"), ("a/b", "slashes"), (_BUILTIN, "built-in"), ("Taken", "already exists")):
            filepath, problem = exporter_preset._new_preset_filepath(name)
            self.assertIsNone(filepath, name)
            self.assertIn(fragment, problem, name)

    def test_unique_name_counts_up_past_existing_presets(self):
        self.assertEqual(exporter_preset._unique_preset_name("Fresh"), "Fresh")
        self.duplicate(_BUILTIN, "Fresh")
        self.assertEqual(exporter_preset._unique_preset_name("Fresh"), "Fresh 2")
        self.duplicate(_BUILTIN, "Fresh 2")
        self.assertEqual(exporter_preset._unique_preset_name("Fresh"), "Fresh 3")

    def test_unique_name_never_returns_a_builtin_name(self):
        self.assertNotEqual(exporter_preset._unique_preset_name(_BUILTIN), _BUILTIN)

    def test_dialog_shows_the_problem_with_the_typed_name(self):
        self.duplicate(_BUILTIN, "Taken")
        context = SimpleNamespace(window_manager=self.wm)
        for name, expect_error in (("Taken", True), ("Brand New", False)):
            layout = _RecordingLayout()
            dialog = SimpleNamespace(layout=layout, name=name)
            exporter_preset.SIMPLE_EXPORT_OT_SavePresetFromPreferences.draw(dialog, context)
            self.assertEqual("icon='ERROR'" in layout.drawn, expect_error, name)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
