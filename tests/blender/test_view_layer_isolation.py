"""
Headless Blender tests for ViewLayerIsolation in functions/collection_layer.py
and exporter_bakes_animation in functions/exporter_funcs.py.

Run with:
    blender --background --factory-startup --python tests/blender/test_view_layer_isolation.py

Animation exporters step the scene once per baked frame and re-evaluate the
whole view layer each step, so the export operator keeps only the exported
collection in the view layer (preference "Isolate During Export").

Covers:
  TestIsolate
    - only the target subtree is evaluated; ancestors stay included,
      every other collection is excluded, loose scene-root objects disabled
    - switching targets re-includes the new one and restores its subtree
    - an originally excluded target or ancestor is included and reported
    - an armature in an excluded collection or disabled in the scene root
      still deforms the target mesh (dependency pull-in)

  TestRestore
    - restore() brings back every original exclude flag, including flags
      inside an excluded parent and an originally excluded target
    - several isolate() calls in a row restore to the state before the first
    - root objects that were already hidden stay hidden

  TestExporterBakesAnimation
    - glTF / FBX / USD animation flags, the Alembic frame range, static STL
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

from simple_export.functions.collection_layer import ViewLayerIsolation  # noqa: E402
from simple_export.functions.exporter_funcs import exporter_bakes_animation  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _new_collection(name, parent):
    col = bpy.data.collections.new(name)
    parent.children.link(col)
    return col


def _new_object(name, collection, data=None):
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj)
    return obj


def _layer_collection(name):
    def find(lc):
        if lc.name == name:
            return lc
        for child in lc.children:
            found = find(child)
            if found:
                return found
        return None
    return find(bpy.context.view_layer.layer_collection)


def _exclude_state():
    state = {}

    def walk(lc, path):
        for child in lc.children:
            child_path = path + (child.name,)
            state[child_path] = child.exclude
            walk(child, child_path)

    walk(bpy.context.view_layer.layer_collection, ())
    return state


class _SceneFixture(unittest.TestCase):
    """
    Scene Collection
    ├── loose_obj
    ├── level
    │   ├── npcs
    │   │   ├── npc_a        (npc_a_mesh, npc_a_sub/npc_a_prop)
    │   │   └── npc_b        (npc_b_mesh)
    │   └── props            (prop_obj)
    └── rigs                 (rig_a, armature of npc_a_mesh)
    """

    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.scene = bpy.context.scene
        root = self.scene.collection

        self.level = _new_collection("level", root)
        self.npcs = _new_collection("npcs", self.level)
        self.npc_a = _new_collection("npc_a", self.npcs)
        self.npc_a_sub = _new_collection("npc_a_sub", self.npc_a)
        self.npc_b = _new_collection("npc_b", self.npcs)
        self.props = _new_collection("props", self.level)
        self.rigs = _new_collection("rigs", root)

        self.loose = _new_object("loose_obj", root)
        self.npc_a_mesh = _new_object("npc_a_mesh", self.npc_a, bpy.data.meshes.new("npc_a_mesh"))
        _new_object("npc_a_prop", self.npc_a_sub)
        _new_object("npc_b_mesh", self.npc_b, bpy.data.meshes.new("npc_b_mesh"))
        _new_object("prop_obj", self.props)
        self.rig = _new_object("rig_a", self.rigs, bpy.data.armatures.new("rig_a"))
        self._skin_to_rig()

        self.isolation = ViewLayerIsolation(bpy.context.view_layer, self.scene)

    def _skin_to_rig(self):
        """npc_a_mesh = one quad fully weighted to bone 'b' of rig_a."""
        bpy.context.view_layer.objects.active = self.rig
        bpy.ops.object.mode_set(mode='EDIT')
        bone = self.rig.data.edit_bones.new("b")
        bone.head, bone.tail = (0, 0, 0), (0, 0, 1)
        bpy.ops.object.mode_set(mode='OBJECT')

        mesh = self.npc_a_mesh.data
        mesh.from_pydata([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)], [], [(0, 1, 2, 3)])
        group = self.npc_a_mesh.vertex_groups.new(name="b")
        group.add(range(4), 1.0, 'REPLACE')
        mod = self.npc_a_mesh.modifiers.new("Armature", 'ARMATURE')
        mod.object = self.rig

    def tearDown(self):
        self.isolation.restore()

    def evaluated_mesh_names(self):
        """Mesh objects the depsgraph evaluates for the view layer (the cost of
        a baked frame). Excluded collections and viewport-disabled objects
        drop out; dependencies such as the armature are pulled in regardless."""
        depsgraph = bpy.context.evaluated_depsgraph_get()
        depsgraph.update()
        return {ob.original.name for ob in depsgraph.objects if ob.type == 'MESH'}

    def evaluated_names(self):
        depsgraph = bpy.context.evaluated_depsgraph_get()
        depsgraph.update()
        return {ob.original.name for ob in depsgraph.objects}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestIsolate(_SceneFixture):

    def test_only_target_subtree_evaluated(self):
        self.isolation.isolate("npc_a")
        self.assertEqual(self.evaluated_mesh_names(), {"npc_a_mesh"})
        self.assertNotIn("loose_obj", self.evaluated_names())
        self.assertNotIn("prop_obj", self.evaluated_names())

    def test_ancestors_stay_included_siblings_excluded(self):
        self.isolation.isolate("npc_a")
        for name in ("level", "npcs", "npc_a", "npc_a_sub"):
            self.assertFalse(_layer_collection(name).exclude, name)
        for name in ("npc_b", "props", "rigs"):
            self.assertTrue(_layer_collection(name).exclude, name)

    def test_loose_root_object_disabled(self):
        self.isolation.isolate("npc_a")
        self.assertTrue(self.loose.hide_viewport)

    def test_switching_target(self):
        self.isolation.isolate("npc_a")
        self.isolation.isolate("npc_b")
        self.assertEqual(self.evaluated_mesh_names(), {"npc_b_mesh"})
        self.assertFalse(_layer_collection("npc_b").exclude)
        self.assertTrue(_layer_collection("npc_a").exclude)
        self.assertTrue(self.loose.hide_viewport)

    def test_switching_back_restores_target_subtree(self):
        # npc_a_sub was not excluded originally: it must come back with npc_a
        self.isolation.isolate("npc_a")
        self.isolation.isolate("npc_b")
        self.isolation.isolate("npc_a")
        self.assertFalse(_layer_collection("npc_a_sub").exclude)

    def test_target_subtree_keeps_original_exclude(self):
        _layer_collection("npc_a_sub").exclude = True
        self.isolation.isolate("npc_b")
        self.isolation.isolate("npc_a")
        self.assertTrue(_layer_collection("npc_a_sub").exclude)

    def test_excluded_target_is_included_and_reported(self):
        _layer_collection("npc_b").exclude = True
        self.assertTrue(self.isolation.isolate("npc_b"))
        self.assertFalse(_layer_collection("npc_b").exclude)
        self.assertEqual(self.evaluated_mesh_names(), {"npc_b_mesh"})

    def test_excluded_ancestor_is_reported(self):
        _layer_collection("npcs").exclude = True
        self.assertTrue(self.isolation.isolate("npc_a"))
        self.assertEqual(self.evaluated_mesh_names(), {"npc_a_mesh"})

    def test_included_target_not_reported_after_switch(self):
        # npc_b is excluded by the first isolate, not by the user
        self.isolation.isolate("npc_a")
        self.assertFalse(self.isolation.isolate("npc_b"))

    def test_armature_outside_target_still_deforms(self):
        self.isolation.isolate("npc_a")
        self.assertTrue(_layer_collection("rigs").exclude)
        self.assert_rig_deforms()

    def assert_rig_deforms(self):
        self.rig.pose.bones["b"].location = (2, 2, 2)
        depsgraph = bpy.context.evaluated_depsgraph_get()
        depsgraph.update()
        mesh_eval = self.npc_a_mesh.evaluated_get(depsgraph).data
        self.assertTrue(any(abs(v.co.x - o.co.x) > 0.5 or abs(v.co.y - o.co.y) > 0.5
                            or abs(v.co.z - o.co.z) > 0.5
                            for v, o in zip(mesh_eval.vertices, self.npc_a_mesh.data.vertices)),
                        "armature excluded from the view layer no longer deforms the mesh")

    def test_armature_in_scene_root_still_deforms(self):
        self.rigs.objects.unlink(self.rig)
        self.scene.collection.objects.link(self.rig)
        self.isolation.isolate("npc_a")
        self.assertTrue(self.rig.hide_viewport)
        self.assert_rig_deforms()

    def test_unknown_collection_is_ignored(self):
        before = _exclude_state()
        self.assertFalse(self.isolation.isolate("does_not_exist"))
        self.assertEqual(_exclude_state(), before)
        self.assertFalse(self.isolation.active)


class TestRestore(_SceneFixture):

    def test_restore_after_one_isolate(self):
        before = _exclude_state()
        self.isolation.isolate("npc_a")
        self.isolation.restore()
        self.assertEqual(_exclude_state(), before)
        self.assertFalse(self.loose.hide_viewport)
        self.assertFalse(self.isolation.active)
        self.assertEqual(self.evaluated_mesh_names(), {"npc_a_mesh", "npc_b_mesh"})
        self.assertIn("loose_obj", self.evaluated_names())

    def test_restore_after_several_isolates(self):
        before = _exclude_state()
        for name in ("npc_a", "npc_b", "props", "npc_a_sub"):
            self.isolation.isolate(name)
        self.isolation.restore()
        self.assertEqual(_exclude_state(), before)

    def test_restore_keeps_original_excludes(self):
        # excluded parent, excluded target, excluded child inside an included parent
        _layer_collection("npc_a_sub").exclude = True
        _layer_collection("props").exclude = True
        _layer_collection("npc_b").exclude = True
        before = _exclude_state()

        self.isolation.isolate("npc_b")
        self.isolation.isolate("npc_a")
        self.isolation.restore()
        self.assertEqual(_exclude_state(), before)

    def test_restore_keeps_hidden_root_object_hidden(self):
        self.loose.hide_viewport = True
        self.isolation.isolate("npc_a")
        self.isolation.restore()
        self.assertTrue(self.loose.hide_viewport)

    def test_restore_without_isolate_is_noop(self):
        before = _exclude_state()
        self.isolation.restore()
        self.assertEqual(_exclude_state(), before)


class TestExporterBakesAnimation(unittest.TestCase):

    def setUp(self):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        self.col = _new_collection("export_col", bpy.context.scene.collection)
        bpy.context.view_layer.active_layer_collection = _layer_collection("export_col")

    def add_exporter(self, handler):
        before = len(self.col.exporters)
        bpy.ops.collection.exporter_add(name=handler)
        if len(self.col.exporters) == before:
            self.skipTest(f"exporter {handler} not available")
        return self.col.exporters[-1]

    def assert_flag(self, handler, attr):
        exporter = self.add_exporter(handler)
        setattr(exporter.export_properties, attr, True)
        self.assertTrue(exporter_bakes_animation(exporter), handler)
        setattr(exporter.export_properties, attr, False)
        self.assertFalse(exporter_bakes_animation(exporter), handler)

    def test_gltf(self):
        self.assert_flag("IO_FH_gltf2", "export_animations")

    def test_fbx(self):
        self.assert_flag("IO_FH_fbx", "bake_anim")

    def test_usd(self):
        self.assert_flag("IO_FH_usd", "export_animation")

    def test_alembic_frame_range(self):
        props = self.add_exporter("IO_FH_alembic").export_properties
        props.start, props.end = 1, 250
        self.assertTrue(exporter_bakes_animation(self.col.exporters[-1]))
        props.start, props.end = 10, 10
        self.assertFalse(exporter_bakes_animation(self.col.exporters[-1]))

    def test_static_format(self):
        self.assertFalse(exporter_bakes_animation(self.add_exporter("IO_FH_stl")))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
