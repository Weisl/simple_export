"""
Headless Blender tests for skip_render_hidden_objects in functions/gltf_instance_filter.py.

Run with:
    blender --background --factory-startup --python tests/blender/test_gltf_instance_filter.py

Blender's glTF exporter applies Renderable Objects only to objects the scene holds directly; objects that come in
through a collection instance inherit the instancer's result. The Skip Render-Hidden Objects pre-export operation
makes hidden-for-render objects drop out, also inside an instance (colliders, boolean cutters).

Covers:
  TestSkipRenderHiddenObjects
    - without the filter, a hide_render mesh inside an instance is exported, even with Renderable Objects on
      (the Blender behaviour it works around)
    - with the filter, it is dropped and the renderable mesh stays, with Renderable Objects on or off
    - the exporter's filter method is restored afterwards, also when the export raises
"""

import json
import os
import shutil
import struct
import sys
import tempfile
import unittest

import bpy

_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_TESTS_DIR = os.path.dirname(_FILE_DIR)
_ADDON_ROOT = os.path.dirname(_TESTS_DIR)
_EXTENSIONS_ROOT = os.path.dirname(_ADDON_ROOT)
if _EXTENSIONS_ROOT not in sys.path:
    sys.path.insert(0, _EXTENSIONS_ROOT)
if _ADDON_ROOT not in sys.path:
    sys.path.insert(0, _ADDON_ROOT)

from simple_export.functions.gltf_instance_filter import (  # noqa: E402
    skip_render_hidden_objects, _gltf_tree_class,
)


def _glb_node_names(path):
    with open(path, "rb") as f:
        f.read(12)
        length, _ = struct.unpack("<II", f.read(8))
        data = json.loads(f.read(length))
    return {n.get("name") for n in data.get("nodes", [])}


class TestSkipRenderHiddenObjects(unittest.TestCase):

    def setUp(self):
        if _gltf_tree_class() is None:
            self.skipTest("glTF exporter tree class not found in this Blender build")
        self.tmpdir = tempfile.mkdtemp(prefix="se_gltf_filter_")
        scene = bpy.context.scene

        # Source collection (not in the scene) with a renderable mesh and a hidden-for-render collider
        self.source = bpy.data.collections.new("gate_source")
        for name, hidden in (("gate_body", False), ("UBX_gate_flap", True)):
            obj = bpy.data.objects.new(name, bpy.data.meshes.new(name))
            obj.hide_render = hidden
            self.source.objects.link(obj)

        # Export collection holding one instance of the source
        self.export_col = bpy.data.collections.new("gates_export")
        scene.collection.children.link(self.export_col)
        self.instancer = bpy.data.objects.new("gate_instance", None)
        self.instancer.instance_type = 'COLLECTION'
        self.instancer.instance_collection = self.source
        self.export_col.objects.link(self.instancer)

    def tearDown(self):
        for obj in list(self.source.objects) + [self.instancer]:
            bpy.data.objects.remove(obj)
        bpy.data.collections.remove(self.export_col)
        bpy.data.collections.remove(self.source)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _export(self, name, use_renderable, filtered):
        path = os.path.join(self.tmpdir, name + ".glb")
        kwargs = dict(filepath=path, export_format='GLB', collection=self.export_col.name,
                      use_renderable=use_renderable)
        if filtered:
            with skip_render_hidden_objects():
                bpy.ops.export_scene.gltf(**kwargs)
        else:
            bpy.ops.export_scene.gltf(**kwargs)
        return _glb_node_names(path)

    def test_blender_exports_hidden_instanced_objects(self):
        names = self._export("plain", use_renderable=True, filtered=False)
        self.assertIn("UBX_gate_flap", names, "Blender behaviour changed: the workaround may no longer be needed")

    def test_filter_drops_hidden_instanced_objects(self):
        names = self._export("filtered", use_renderable=True, filtered=True)
        self.assertNotIn("UBX_gate_flap", names)
        self.assertIn("gate_body", names)

    def test_filter_works_without_renderable(self):
        names = self._export("not_renderable", use_renderable=False, filtered=True)
        self.assertNotIn("UBX_gate_flap", names)
        self.assertIn("gate_body", names)

    def test_original_method_restored(self):
        tree_class = _gltf_tree_class()
        original = tree_class.node_filter_not_inheritable_is_kept
        with self.assertRaises(RuntimeError):
            with skip_render_hidden_objects():
                self.assertIsNot(tree_class.node_filter_not_inheritable_is_kept, original)
                raise RuntimeError("export failed")
        self.assertIs(tree_class.node_filter_not_inheritable_is_kept, original)


if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
