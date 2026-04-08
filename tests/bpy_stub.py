"""
Installs minimal bpy and Blender-internal stubs into sys.modules so that
addon submodules can be imported outside of Blender.

Import this module before importing anything from simple_export.
"""

import sys
import types
from unittest.mock import MagicMock

_BLENDER_MOCK_MODULES = [
    "bpy",
    "bpy.app",
    "bpy.app.handlers",
    "bpy.types",
    "bpy.props",
    "bpy.utils",
    "bpy.path",
    "bl_operators",
    "bl_operators.presets",
    "bpy_extras",
    "bpy_extras.io_utils",
    "gpu",
    "mathutils",
]

# ---------------------------------------------------------------------------
# Single shared metaclass for all Blender base types.
#
# Addon classes inherit from Blender types such as bpy.types.Operator,
# bpy.types.Menu, and bl_operators.presets.AddPresetBase.  A class that
# inherits from multiple bases requires the metaclass of the derived class
# to be a (non-strict) subclass of *all* its bases' metaclasses.
#
# Using plain MagicMock for those bases triggers a conflict because
# MagicMock's metaclass differs from `type`.  We instead use a single
# custom metaclass (_BlenderMeta) that:
#   - is a subclass of `type`  →  compatible with all normal Python classes
#   - returns a MagicMock for any missing class-level attribute access
#     (e.g. Menu.draw_preset, AddPresetBase.bl_idname)
#
# All stub base classes share this one metaclass, so Python's "most-derived
# metaclass wins" rule is trivially satisfied.
# ---------------------------------------------------------------------------

_BlenderMeta = type(
    "_BlenderMeta",
    (type,),
    {"__getattr__": lambda cls, name: MagicMock(name=f"{cls.__name__}.{name}")},
)

_BLENDER_BASE_NAMES = [
    "Operator", "Panel", "Menu", "UIList", "Header",
    "PropertyGroup", "AddonPreferences", "WorkSpaceTool",
]
_BLENDER_IO_NAMES = ["ImportHelper", "ExportHelper"]


def _make_blender_base_types():
    """Return a dict of stub Blender type base classes keyed by name."""
    return {name: _BlenderMeta(name, (), {}) for name in _BLENDER_BASE_NAMES}


def _make_bpy_mock(blender_version=(5, 1, 0), user_path="/tmp/blender_user"):
    """Return a configured bpy MagicMock."""
    mock = MagicMock(name="bpy")
    mock.app.version = blender_version
    mock.utils.resource_path.return_value = user_path
    mock.context.preferences.addons.get.return_value = None
    mock.app.handlers.persistent = lambda f: f
    for name, cls in _make_blender_base_types().items():
        setattr(mock.types, name, cls)
    return mock


def install(blender_version=(5, 1, 0), user_path="/tmp/blender_user"):
    """Install bpy stubs into sys.modules. Safe to call multiple times."""
    if "bpy" in sys.modules:
        # Update version on existing mock
        sys.modules["bpy"].app.version = blender_version
        sys.modules["bpy"].utils.resource_path.return_value = user_path
        return

    bpy_mock = _make_bpy_mock(blender_version, user_path)
    sys.modules["bpy"] = bpy_mock

    # Submodule stubs so `from bpy.xxx import yyy` resolves correctly
    app_handlers = MagicMock(name="bpy.app.handlers")
    app_handlers.persistent = lambda f: f
    sys.modules["bpy.app"] = MagicMock(name="bpy.app")
    sys.modules["bpy.app.handlers"] = app_handlers

    bpy_types = MagicMock(name="bpy.types")
    for name, cls in _make_blender_base_types().items():
        setattr(bpy_types, name, cls)
    sys.modules["bpy.types"] = bpy_types

    sys.modules["bpy.props"] = MagicMock(name="bpy.props")
    sys.modules["bpy.utils"] = MagicMock(name="bpy.utils")
    sys.modules["bpy.path"] = MagicMock(name="bpy.path")

    sys.modules["bl_operators"] = MagicMock(name="bl_operators")
    bl_presets_mock = MagicMock(name="bl_operators.presets")
    bl_presets_mock.AddPresetBase = _BlenderMeta("AddPresetBase", (), {})
    sys.modules["bl_operators.presets"] = bl_presets_mock

    sys.modules["bpy_extras"] = MagicMock(name="bpy_extras")
    io_utils_mock = MagicMock(name="bpy_extras.io_utils")
    io_utils_mock.ImportHelper = _BlenderMeta("ImportHelper", (), {})
    io_utils_mock.ExportHelper = _BlenderMeta("ExportHelper", (), {})
    sys.modules["bpy_extras.io_utils"] = io_utils_mock

    sys.modules["gpu"] = MagicMock(name="gpu")
    sys.modules["mathutils"] = MagicMock(name="mathutils")


def make_simple_export_package():
    """
    Register a minimal simple_export package stub so relative imports work
    without executing the full addon __init__.py (which requires Blender).
    """
    import os

    addon_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if "simple_export" not in sys.modules:
        pkg = types.ModuleType("simple_export")
        pkg.__path__ = [addon_root]
        pkg.__package__ = "simple_export"
        pkg.__spec__ = None
        sys.modules["simple_export"] = pkg
