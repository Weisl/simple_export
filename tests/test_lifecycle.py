"""
Tests for addon register, unregister, and reload lifecycle.

Covers:
  - register() calls every submodule's register() in the correct order
  - unregister() calls every submodule's unregister() in reverse register order
  - First-import path: submodules are imported via 'from . import'
  - Blender-reload path: submodules are reloaded via importlib.reload()
"""

import importlib
import importlib.util
import os
import sys
import types
import unittest
from unittest.mock import MagicMock, call, patch

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

_ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXTENSIONS_ROOT = os.path.dirname(_ADDON_ROOT)

if _EXTENSIONS_ROOT not in sys.path:
    sys.path.insert(0, _EXTENSIONS_ROOT)

from tests.bpy_stub import install as _install_bpy

_install_bpy(blender_version=(5, 1, 0))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Submodules in the order __init__.py registers them.
_SUBMODULES = ["operators", "ui", "preferences", "core", "presets_export", "presets_addon"]


def _make_mock_submodules():
    """Return a dict of MagicMock objects keyed by submodule short name."""
    return {name: MagicMock(name=f"simple_export.{name}") for name in _SUBMODULES}


def _load_addon(mocks):
    """
    Execute simple_export/__init__.py with mocked submodules injected into
    sys.modules.  Returns the loaded module object.
    """
    # Remove any leftover simple_export entries from previous tests.
    for key in list(sys.modules):
        if key == "simple_export" or key.startswith("simple_export."):
            del sys.modules[key]

    # Pre-populate sys.modules so 'from . import X' resolves to our mocks.
    for name, mock in mocks.items():
        sys.modules[f"simple_export.{name}"] = mock

    spec = importlib.util.spec_from_file_location(
        "simple_export",
        os.path.join(_ADDON_ROOT, "__init__.py"),
        submodule_search_locations=[_ADDON_ROOT],
    )
    addon = importlib.util.module_from_spec(spec)
    addon.__package__ = "simple_export"
    sys.modules["simple_export"] = addon
    spec.loader.exec_module(addon)
    return addon, spec


# ---------------------------------------------------------------------------
# 1. register()
# ---------------------------------------------------------------------------

class TestRegister(unittest.TestCase):
    def setUp(self):
        self.mocks = _make_mock_submodules()
        self.addon, _ = _load_addon(self.mocks)

    def tearDown(self):
        for key in list(sys.modules):
            if key == "simple_export" or key.startswith("simple_export."):
                del sys.modules[key]

    def test_register_calls_every_submodule(self):
        self.addon.register()
        for name in _SUBMODULES:
            self.mocks[name].register.assert_called_once_with()

    def test_register_order(self):
        order = []
        for name in _SUBMODULES:
            self.mocks[name].register.side_effect = lambda n=name: order.append(n)
        self.addon.register()
        self.assertEqual(order, _SUBMODULES)


# ---------------------------------------------------------------------------
# 2. unregister()
# ---------------------------------------------------------------------------

class TestUnregister(unittest.TestCase):
    def setUp(self):
        self.mocks = _make_mock_submodules()
        self.addon, _ = _load_addon(self.mocks)

    def tearDown(self):
        for key in list(sys.modules):
            if key == "simple_export" or key.startswith("simple_export."):
                del sys.modules[key]

    def test_unregister_calls_every_submodule(self):
        self.addon.unregister()
        for name in _SUBMODULES:
            self.mocks[name].unregister.assert_called_once_with()

    def test_unregister_order_is_reverse_of_register(self):
        order = []
        for name in _SUBMODULES:
            self.mocks[name].unregister.side_effect = lambda n=name: order.append(n)
        self.addon.unregister()
        self.assertEqual(order, list(reversed(_SUBMODULES)))

    def test_register_then_unregister_each_called_once(self):
        self.addon.register()
        self.addon.unregister()
        for name in _SUBMODULES:
            self.mocks[name].register.assert_called_once_with()
            self.mocks[name].unregister.assert_called_once_with()


# ---------------------------------------------------------------------------
# 3. Reload
# ---------------------------------------------------------------------------

class TestReload(unittest.TestCase):
    def setUp(self):
        self.mocks = _make_mock_submodules()
        self.addon, self.spec = _load_addon(self.mocks)

    def tearDown(self):
        for key in list(sys.modules):
            if key == "simple_export" or key.startswith("simple_export."):
                del sys.modules[key]

    def test_first_import_path_imports_submodules(self):
        """On a fresh import (no 'bpy' in module namespace) each submodule is
        bound as an attribute via 'from . import'."""
        for name in _SUBMODULES:
            self.assertIs(
                getattr(self.addon, name),
                self.mocks[name],
                f"addon.{name} should be the mock submodule after first import",
            )

    def test_reload_blender_path_reloads_submodules(self):
        """When 'bpy' is present in the module namespace (simulating Blender's
        reload), importlib.reload is called for every submodule."""
        # Simulate Blender having injected 'bpy' into the addon namespace.
        self.addon.bpy = sys.modules["bpy"]

        with patch("importlib.reload") as mock_reload:
            self.spec.loader.exec_module(self.addon)

        reloaded = [c.args[0] for c in mock_reload.call_args_list]
        for name in _SUBMODULES:
            self.assertIn(
                self.mocks[name],
                reloaded,
                f"importlib.reload not called for submodule '{name}'",
            )

    def test_reload_blender_path_reloads_in_declaration_order(self):
        """Submodules must be reloaded in the same order they are declared."""
        self.addon.bpy = sys.modules["bpy"]

        with patch("importlib.reload") as mock_reload:
            self.spec.loader.exec_module(self.addon)

        reloaded = [c.args[0] for c in mock_reload.call_args_list]
        expected = [self.mocks[n] for n in _SUBMODULES]
        self.assertEqual(reloaded, expected)

    def test_reload_preserves_register_and_unregister(self):
        """After a standard importlib.reload the module still exposes
        register() and unregister()."""
        importlib.reload(self.addon)
        self.assertTrue(callable(self.addon.register))
        self.assertTrue(callable(self.addon.unregister))

    def test_register_works_after_reload(self):
        importlib.reload(self.addon)
        self.addon.register()
        for name in _SUBMODULES:
            self.mocks[name].register.assert_called()


if __name__ == "__main__":
    unittest.main()
