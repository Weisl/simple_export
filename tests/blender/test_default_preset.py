"""
Headless Blender tests for the addon's default preset selection.

Run with:
    blender --background --factory-startup --python tests/blender/test_default_preset.py

The "Default Preset" preference is an enum whose built-in default is an index
baked in when the module is imported. On a fresh install the preset folder is
still empty at that point, so the index is meaningless.
pin_default_preset_if_unset() selects DEFAULT_ADDON_PRESET once the files exist,
unless the user already chose a preset.
"""

import os
import sys
import unittest

import bpy  # noqa: F401

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

import tests.blender._helpers  # noqa: F401,E402  (shared headless-test setup)

from simple_export import presets_addon  # noqa: E402
from simple_export.core.info import DEFAULT_ADDON_PRESET  # noqa: E402
from simple_export.presets_addon.preset_data_exporters import presets_simple_exporter  # noqa: E402
from simple_export.preferences import preferenecs  # noqa: E402

_FOLDER = os.path.join(os.sep, "presets", "simple_export")


class _FakePrefs:
    """Stands in for the addon preferences: only what pin_default_preset_if_unset touches."""

    def __init__(self, is_set, value=""):
        self._is_set = is_set
        self._value = value

    def is_property_set(self, name):
        assert name == "simple_export_default_preset"
        return self._is_set

    @property
    def simple_export_default_preset(self):
        return self._value

    @simple_export_default_preset.setter
    def simple_export_default_preset(self, value):
        self._value = value
        self._is_set = True


class TestDefaultPreset(unittest.TestCase):
    def setUp(self):
        self._orig_files = preferenecs.get_simple_export_preset_files
        # Deliberately not alphabetical: the real listing order is arbitrary.
        names = ["Unity-animation", "UE-default", DEFAULT_ADDON_PRESET, "Godot-default"]
        preferenecs.get_simple_export_preset_files = lambda self, context: [
            (os.path.join(_FOLDER, f"{name}.py"), f"{name}.py", "") for name in names
        ]

    def tearDown(self):
        preferenecs.get_simple_export_preset_files = self._orig_files

    def test_default_is_a_shipped_basic_fbx_preset(self):
        self.assertIn(DEFAULT_ADDON_PRESET, presets_simple_exporter)
        self.assertEqual(presets_simple_exporter[DEFAULT_ADDON_PRESET]["export_format"], "FBX")

    def test_unset_preference_is_pinned_to_default(self):
        prefs = _FakePrefs(is_set=False, value=os.path.join(_FOLDER, "Unity-animation.py"))
        presets_addon.pin_default_preset_if_unset(prefs)
        self.assertEqual(prefs.simple_export_default_preset,
                         os.path.join(_FOLDER, f"{DEFAULT_ADDON_PRESET}.py"))

    def test_users_choice_is_kept(self):
        chosen = os.path.join(_FOLDER, "UE-default.py")
        prefs = _FakePrefs(is_set=True, value=chosen)
        presets_addon.pin_default_preset_if_unset(prefs)
        self.assertEqual(prefs.simple_export_default_preset, chosen)

    def test_missing_default_file_leaves_preference_alone(self):
        preferenecs.get_simple_export_preset_files = lambda self, context: [
            (os.path.join(_FOLDER, "UE-default.py"), "UE-default.py", ""),
        ]
        current = os.path.join(_FOLDER, "UE-default.py")
        prefs = _FakePrefs(is_set=False, value=current)
        presets_addon.pin_default_preset_if_unset(prefs)
        self.assertEqual(prefs.simple_export_default_preset, current)
        self.assertFalse(prefs.is_property_set("simple_export_default_preset"))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
