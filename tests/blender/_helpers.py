"""
Shared helpers for headless Blender tests.

All test files in this package are meant to be executed directly by Blender:

    blender --background --python tests/blender/test_xxx.py

This module is imported by each test file before any test class is defined.
It puts the addon's parent directory on sys.path so ``import simple_export``
resolves, and provides registration / fixture helpers that avoid repeating
boilerplate across test modules.
"""

import os
import sys

import bpy

# ---------------------------------------------------------------------------
# sys.path bootstrap
# ---------------------------------------------------------------------------

_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_TESTS_DIR = os.path.dirname(_FILE_DIR)
_ADDON_ROOT = os.path.dirname(_TESTS_DIR)
_EXTENSIONS_ROOT = os.path.dirname(_ADDON_ROOT)

if _EXTENSIONS_ROOT not in sys.path:
    sys.path.insert(0, _EXTENSIONS_ROOT)
# _ADDON_ROOT must also be on the path so the `tests` package is importable.
if _ADDON_ROOT not in sys.path:
    sys.path.insert(0, _ADDON_ROOT)

# ---------------------------------------------------------------------------
# Collection-property helpers
# ---------------------------------------------------------------------------

from simple_export.preferences.collection_setup import (  # noqa: E402
    CollectionPreExportOps,
    _PRE_EXPORT_BOOL_DEFAULTS,
    _PRE_ROTATE_EULER_DEFAULT,
)

# Scene-level migration source props (mirrors what preferenecs.py registers,
# but only the subset consumed by ensure_collection_properties).
_SCENE_MIGRATION_BOOL_PROPS = dict(_PRE_EXPORT_BOOL_DEFAULTS)


def register_collection_props():
    """Register CollectionPreExportOps and the Collection pointer/bool props."""
    bpy.utils.register_class(CollectionPreExportOps)
    bpy.types.Collection.pre_export_ops = bpy.props.PointerProperty(
        type=CollectionPreExportOps
    )
    bpy.types.Collection.use_root_object = bpy.props.BoolProperty(
        name="Use Root Object", default=True
    )


def unregister_collection_props():
    """Unregister CollectionPreExportOps and the Collection props."""
    if hasattr(bpy.types.Collection, "pre_export_ops"):
        del bpy.types.Collection.pre_export_ops
    if hasattr(bpy.types.Collection, "use_root_object"):
        del bpy.types.Collection.use_root_object
    try:
        bpy.utils.unregister_class(CollectionPreExportOps)
    except RuntimeError:
        pass


def register_scene_migration_props():
    """Register the scene-level bool/euler props that migration reads from."""
    for attr, default in _SCENE_MIGRATION_BOOL_PROPS.items():
        setattr(
            bpy.types.Scene,
            attr,
            bpy.props.BoolProperty(default=default),
        )
    bpy.types.Scene.pre_rotate_euler = bpy.props.FloatVectorProperty(
        subtype="EULER",
        default=(0.0, 0.0, 0.0),
    )


def unregister_scene_migration_props():
    """Remove the scene-level migration props."""
    for attr in _SCENE_MIGRATION_BOOL_PROPS:
        if hasattr(bpy.types.Scene, attr):
            delattr(bpy.types.Scene, attr)
    if hasattr(bpy.types.Scene, "pre_rotate_euler"):
        del bpy.types.Scene.pre_rotate_euler


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def make_collection(name="TestCol"):
    """Create a named collection, link it to the active scene, return it."""
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def remove_collection(col):
    """Safely remove a collection from bpy.data."""
    try:
        bpy.data.collections.remove(col)
    except Exception:
        pass


def make_mesh_object(name="TestObj", location=(0.0, 0.0, 0.0)):
    """Create a plain mesh object, link it to the active scene, return it."""
    mesh = bpy.data.meshes.new(name + "_mesh")
    obj = bpy.data.objects.new(name, mesh)
    obj.location = location
    bpy.context.scene.collection.objects.link(obj)
    return obj


def remove_object(obj):
    """Safely remove a mesh object and its mesh data from bpy.data."""
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
