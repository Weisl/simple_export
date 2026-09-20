"""
Headless Blender tests for copying export settings between collections.

Run with:
    blender --background --factory-startup --python tests/blender/test_copy_export_settings.py

Exercises functions/copy_settings.py and operators/copy_export_settings_ops.py against real
collection exporters. Like test_preset_application.py, only the minimal set of Blender types
the code needs is registered, not the full addon.

Covers:

  TestCopyRnaProperties
    - Writable properties are copied, properties in the skip set are not
    - Vector properties (Euler) are copied
    - Properties the target does not have are returned as failures, not raised

  TestCopyCollectionExportSettings
    - Same format: settings copied, the target's file path is untouched
    - Different format: target converted, folder and file name kept, extension swapped
    - glTF binary vs separate decides between .glb and .gltf
    - A directory-only path survives a conversion
    - Target without an exporter gets one of the source's format and an empty path
    - Pre-export operations, user group and preset labels are copied
    - Each part is left alone when switched off

  TestCopyExportSettingsOperator
    - Registered under bpy.ops.simple_export
    - Missing source / source without exporter / nothing enabled / no targets are refused
    - Copies to every target and leaves the active layer collection as it was
    - Linked (read-only) targets are skipped
"""

import os
import shutil
import sys
import tempfile
import unittest
import warnings

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

_ops_mod = None

_EXTRA_COLLECTION_PROPS = {
    "simple_export_export_preset": lambda: bpy.props.StringProperty(default=""),
    "simple_export_addon_preset": lambda: bpy.props.StringProperty(default=""),
    "export_group_name": lambda: bpy.props.StringProperty(default=""),
}


def _load_operator_module(filename):
    import importlib.util as _ilu
    mod_name = f"simple_export.operators.{filename[:-3]}"
    sys.modules.pop(mod_name, None)
    path = os.path.join(_ADDON_ROOT, "operators", filename)
    spec = _ilu.spec_from_file_location(mod_name, path)
    mod = _ilu.module_from_spec(spec)
    mod.__package__ = "simple_export.operators"
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


def setUpModule():
    global _ops_mod
    _h.register_collection_props()
    for attr, make_prop in _EXTRA_COLLECTION_PROPS.items():
        if not hasattr(bpy.types.Collection, attr):
            setattr(bpy.types.Collection, attr, make_prop())
    _ops_mod = _load_operator_module("copy_export_settings_ops.py")
    _ops_mod.register()


def tearDownModule():
    try:
        _ops_mod.unregister()
    except Exception:
        pass
    for attr in _EXTRA_COLLECTION_PROPS:
        if hasattr(bpy.types.Collection, attr):
            delattr(bpy.types.Collection, attr)
    _h.unregister_collection_props()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _FakeOperator:
    """Stands in for the operator create_collection_exporter reports errors through."""

    def __init__(self):
        self.reports = []

    def report(self, kind, message):
        self.reports.append((kind, message))


class _CopyTestBase(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="se_copy_test_")
        self.collections = []
        self.src = self._make_collection("CopySrc")
        self.dst = self._make_collection("CopyDst")

    def tearDown(self):
        for col in self.collections:
            _h.remove_collection(col)
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _make_collection(self, name):
        col = _h.make_collection(name)
        self.collections.append(col)
        return col

    def _add_exporter(self, col, op_name):
        from simple_export.functions.collection_layer import set_active_layer_Collection
        set_active_layer_Collection(col.name)
        try:
            bpy.ops.collection.exporter_add(name=op_name)
        except Exception as exc:
            self.skipTest(f"bpy.ops.collection.exporter_add({op_name!r}) not available: {exc}")
        if not col.exporters:
            self.skipTest(f"exporter_add({op_name!r}) produced no exporters")
        return col.exporters[-1]

    def _copy(self, **kwargs):
        from simple_export.functions.copy_settings import copy_collection_export_settings
        return copy_collection_export_settings(_FakeOperator(), bpy.context, self.src, self.dst, **kwargs)


# ---------------------------------------------------------------------------
# 1. copy_rna_properties
# ---------------------------------------------------------------------------

class TestCopyRnaProperties(_CopyTestBase):

    def test_writable_properties_copied_and_skip_set_respected(self):
        from simple_export.functions.copy_settings import EXPORTER_COPY_SKIP, copy_rna_properties
        source = self._add_exporter(self.src, "IO_FH_fbx").export_properties
        target = self._add_exporter(self.dst, "IO_FH_fbx").export_properties
        source.global_scale = 2.5
        source.filepath = os.path.join(self.tmpdir, "source.fbx")
        target.filepath = os.path.join(self.tmpdir, "target.fbx")

        failed = copy_rna_properties(source, target, skip=EXPORTER_COPY_SKIP)

        self.assertEqual(failed, [])
        self.assertAlmostEqual(target.global_scale, 2.5, places=4)
        self.assertEqual(target.filepath, os.path.join(self.tmpdir, "target.fbx"))

    def test_explicit_skip_leaves_property_untouched(self):
        from simple_export.functions.copy_settings import copy_rna_properties
        source = self._add_exporter(self.src, "IO_FH_fbx").export_properties
        target = self._add_exporter(self.dst, "IO_FH_fbx").export_properties
        source.global_scale = 2.5
        default_scale = target.global_scale

        copy_rna_properties(source, target, skip={'global_scale'})

        self.assertAlmostEqual(target.global_scale, default_scale, places=4)

    def test_euler_vector_property_copied(self):
        from simple_export.functions.copy_settings import copy_rna_properties
        self.src.pre_export_ops.pre_rotate_euler = (0.5, 1.0, 1.5)

        copy_rna_properties(self.src.pre_export_ops, self.dst.pre_export_ops)

        self.assertEqual(tuple(round(v, 4) for v in self.dst.pre_export_ops.pre_rotate_euler), (0.5, 1.0, 1.5))

    def test_property_missing_on_target_is_returned_not_raised(self):
        from simple_export.functions.copy_settings import EXPORTER_COPY_SKIP, copy_rna_properties
        source = self._add_exporter(self.src, "IO_FH_fbx").export_properties
        target = self._add_exporter(self.dst, "IO_FH_gltf2").export_properties

        failed = copy_rna_properties(source, target, skip=EXPORTER_COPY_SKIP)

        self.assertIn('global_scale', failed)


# ---------------------------------------------------------------------------
# 2. copy_collection_export_settings
# ---------------------------------------------------------------------------

class TestCopyCollectionExportSettings(_CopyTestBase):

    def test_same_format_copies_settings_and_keeps_target_path(self):
        source = self._add_exporter(self.src, "IO_FH_fbx")
        target = self._add_exporter(self.dst, "IO_FH_fbx")
        source.export_properties.global_scale = 2.5
        source.export_properties.filepath = os.path.join(self.tmpdir, "source.fbx")
        target.export_properties.filepath = os.path.join(self.tmpdir, "target.fbx")

        result = self._copy()

        self.assertTrue(result['success'], result['message'])
        self.assertEqual(len(self.dst.exporters), 1)
        self.assertAlmostEqual(self.dst.exporters[0].export_properties.global_scale, 2.5, places=4)
        self.assertEqual(self.dst.exporters[0].export_properties.filepath, os.path.join(self.tmpdir, "target.fbx"))

    def test_different_format_converts_target_and_swaps_extension(self):
        source = self._add_exporter(self.src, "IO_FH_fbx")
        source.export_properties.global_scale = 2.5
        target = self._add_exporter(self.dst, "IO_FH_gltf2")
        target.export_properties.filepath = os.path.join(self.tmpdir, "out", "thing.glb")

        result = self._copy()

        self.assertTrue(result['success'], result['message'])
        self.assertEqual(len(self.dst.exporters), 1)
        exporter = self.dst.exporters[0]
        self.assertIn("EXPORT_SCENE_OT_fbx", str(type(exporter.export_properties)))
        self.assertEqual(exporter.export_properties.filepath, os.path.join(self.tmpdir, "out", "thing.fbx"))
        self.assertAlmostEqual(exporter.export_properties.global_scale, 2.5, places=4)

    def test_relative_path_is_kept_when_converting(self):
        self._add_exporter(self.src, "IO_FH_fbx")
        target = self._add_exporter(self.dst, "IO_FH_gltf2")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            target.export_properties.filepath = "//out/thing.glb"

            result = self._copy()

        self.assertTrue(result['success'], result['message'])
        self.assertEqual(self.dst.exporters[0].export_properties.filepath, "//out/thing.fbx")

    def test_gltf_binary_or_separate_decides_the_extension(self):
        source = self._add_exporter(self.src, "IO_FH_gltf2")
        source.export_properties.export_format = 'GLB'
        target = self._add_exporter(self.dst, "IO_FH_fbx")
        target.export_properties.filepath = os.path.join(self.tmpdir, "thing.fbx")

        result = self._copy()

        self.assertTrue(result['success'], result['message'])
        self.assertEqual(self.dst.exporters[0].export_properties.filepath, os.path.join(self.tmpdir, "thing.glb"))

    def test_gltf_separate_gets_gltf_extension(self):
        source = self._add_exporter(self.src, "IO_FH_gltf2")
        source.export_properties.export_format = 'GLTF_SEPARATE'
        target = self._add_exporter(self.dst, "IO_FH_fbx")
        target.export_properties.filepath = os.path.join(self.tmpdir, "thing.fbx")

        result = self._copy()

        self.assertTrue(result['success'], result['message'])
        self.assertEqual(self.dst.exporters[0].export_properties.filepath, os.path.join(self.tmpdir, "thing.gltf"))

    def test_directory_only_path_is_kept_when_converting(self):
        self._add_exporter(self.src, "IO_FH_fbx")
        target = self._add_exporter(self.dst, "IO_FH_gltf2")
        directory = os.path.join(self.tmpdir, "out") + os.sep
        target.export_properties.filepath = directory

        result = self._copy()

        self.assertTrue(result['success'], result['message'])
        self.assertEqual(self.dst.exporters[0].export_properties.filepath, directory)

    def test_target_without_exporter_gets_one_with_an_empty_path(self):
        source = self._add_exporter(self.src, "IO_FH_fbx")
        source.export_properties.global_scale = 2.5
        source.export_properties.filepath = os.path.join(self.tmpdir, "source.fbx")
        self.assertEqual(len(self.dst.exporters), 0)

        result = self._copy()

        self.assertTrue(result['success'], result['message'])
        self.assertEqual(len(self.dst.exporters), 1)
        exporter = self.dst.exporters[0]
        self.assertIn("EXPORT_SCENE_OT_fbx", str(type(exporter.export_properties)))
        self.assertEqual(exporter.export_properties.filepath, "")
        self.assertAlmostEqual(exporter.export_properties.global_scale, 2.5, places=4)

    def test_excluded_target_is_converted_and_excluded_again(self):
        self._add_exporter(self.src, "IO_FH_fbx")
        target = self._add_exporter(self.dst, "IO_FH_gltf2")
        target.export_properties.filepath = os.path.join(self.tmpdir, "thing.glb")
        from simple_export.functions.collection_layer import find_layer_collection_path
        layer_collection = find_layer_collection_path(bpy.context.view_layer.layer_collection, self.dst.name)[-1]
        layer_collection.exclude = True

        result = self._copy()

        self.assertTrue(result['success'], result['message'])
        self.assertIn("EXPORT_SCENE_OT_fbx", str(type(self.dst.exporters[0].export_properties)))
        self.assertTrue(layer_collection.exclude)

    def test_pre_export_ops_group_and_preset_labels_are_copied(self):
        self._add_exporter(self.src, "IO_FH_fbx")
        self._add_exporter(self.dst, "IO_FH_fbx")
        self.src.pre_export_ops.triangulate_before_export = True
        self.src.pre_export_ops.move_by_collection_offset = True
        self.src.export_group_name = "Props"
        self.src.simple_export_export_preset = "UE-default"
        self.src.simple_export_addon_preset = "Unreal-default"

        result = self._copy()

        self.assertTrue(result['success'], result['message'])
        self.assertTrue(self.dst.pre_export_ops.triangulate_before_export)
        self.assertTrue(self.dst.pre_export_ops.move_by_collection_offset)
        self.assertEqual(self.dst.export_group_name, "Props")
        self.assertEqual(self.dst.simple_export_export_preset, "UE-default")
        self.assertEqual(self.dst.simple_export_addon_preset, "Unreal-default")

    def test_switched_off_parts_are_left_alone(self):
        source = self._add_exporter(self.src, "IO_FH_fbx")
        target = self._add_exporter(self.dst, "IO_FH_fbx")
        source.export_properties.global_scale = 2.5
        default_scale = target.export_properties.global_scale
        self.src.pre_export_ops.triangulate_before_export = True
        self.src.export_group_name = "Props"
        self.src.simple_export_export_preset = "UE-default"

        result = self._copy(exporter=False, pre_export=False, group=False)

        self.assertTrue(result['success'], result['message'])
        self.assertAlmostEqual(target.export_properties.global_scale, default_scale, places=4)
        self.assertFalse(self.dst.pre_export_ops.triangulate_before_export)
        self.assertEqual(self.dst.export_group_name, "")
        self.assertEqual(self.dst.simple_export_export_preset, "")

    def test_without_exporter_part_a_target_gets_no_exporter(self):
        self._add_exporter(self.src, "IO_FH_fbx")
        self.src.export_group_name = "Props"

        result = self._copy(exporter=False, pre_export=False)

        self.assertTrue(result['success'], result['message'])
        self.assertEqual(len(self.dst.exporters), 0)
        self.assertEqual(self.dst.export_group_name, "Props")


# ---------------------------------------------------------------------------
# 3. simple_export.copy_export_settings
# ---------------------------------------------------------------------------

class TestCopyExportSettingsOperator(_CopyTestBase):

    def _run(self, source, targets, **kwargs):
        return bpy.ops.simple_export.copy_export_settings(
            'EXEC_DEFAULT',
            source_name=source.name,
            target_names='\n'.join(t.name for t in targets),
            **kwargs,
        )

    def test_operator_accessible_via_bpy_ops(self):
        self.assertTrue(hasattr(bpy.ops.simple_export, "copy_export_settings"))

    def test_missing_source_is_refused(self):
        with self.assertRaises(RuntimeError):
            bpy.ops.simple_export.copy_export_settings('EXEC_DEFAULT', source_name="__nonexistent__",
                                                       target_names=self.dst.name)

    def test_source_without_exporter_is_refused(self):
        self.assertEqual(len(self.src.exporters), 0)
        with self.assertRaises(RuntimeError):
            self._run(self.src, [self.dst])

    def test_source_without_exporter_is_fine_when_only_the_group_is_copied(self):
        self.src.export_group_name = "Props"

        result = self._run(self.src, [self.dst], copy_exporter_settings=False, copy_pre_export_ops=False)

        self.assertEqual(result, {'FINISHED'})
        self.assertEqual(self.dst.export_group_name, "Props")

    def test_nothing_enabled_is_cancelled(self):
        self._add_exporter(self.src, "IO_FH_fbx")

        result = self._run(self.src, [self.dst], copy_exporter_settings=False, copy_pre_export_ops=False,
                           copy_group=False)

        self.assertEqual(result, {'CANCELLED'})

    def test_no_targets_is_cancelled(self):
        self._add_exporter(self.src, "IO_FH_fbx")

        result = bpy.ops.simple_export.copy_export_settings('EXEC_DEFAULT', source_name=self.src.name,
                                                            target_names="")

        self.assertEqual(result, {'CANCELLED'})

    def test_the_source_is_never_its_own_target(self):
        self._add_exporter(self.src, "IO_FH_fbx")

        result = self._run(self.src, [self.src])

        self.assertEqual(result, {'CANCELLED'})

    def test_copies_to_every_target(self):
        source = self._add_exporter(self.src, "IO_FH_fbx")
        source.export_properties.global_scale = 2.5
        third = self._make_collection("CopyThird")
        self._add_exporter(self.dst, "IO_FH_fbx")

        result = self._run(self.src, [self.dst, third])

        self.assertEqual(result, {'FINISHED'})
        for col in (self.dst, third):
            self.assertEqual(len(col.exporters), 1)
            self.assertAlmostEqual(col.exporters[0].export_properties.global_scale, 2.5, places=4)

    def test_active_layer_collection_is_restored(self):
        from simple_export.functions.collection_layer import set_active_layer_Collection
        self._add_exporter(self.src, "IO_FH_fbx")
        # Converting the target activates it internally, so the active one must be put back
        third = self._make_collection("CopyThird")
        set_active_layer_Collection(third.name)

        self._run(self.src, [self.dst])

        self.assertEqual(bpy.context.view_layer.active_layer_collection.name, third.name)

    def test_linked_target_is_skipped(self):
        self._add_exporter(self.src, "IO_FH_fbx")
        self.src.export_group_name = "Props"

        library_col = bpy.data.collections.new("LinkedCol")
        library_path = os.path.join(self.tmpdir, "library.blend")
        bpy.data.libraries.write(library_path, {library_col})
        bpy.data.collections.remove(library_col)
        with bpy.data.libraries.load(library_path, link=True) as (data_from, data_to):
            data_to.collections = ["LinkedCol"]
        linked = data_to.collections[0]
        try:
            self.assertIsNotNone(linked.library)

            self.assertEqual(self._run(self.src, [linked]), {'CANCELLED'})
            self.assertEqual(self._run(self.src, [linked, self.dst]), {'FINISHED'})
            self.assertEqual(self.dst.export_group_name, "Props")
        finally:
            bpy.data.libraries.remove(linked.library)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
