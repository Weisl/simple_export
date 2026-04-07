"""
Tests for the preset loading system.

Covers:
  - Version routing (get_versioned_module selects the right subpackage)
  - All preset modules are importable and have correct structure
  - Preset data completeness (required keys and types)
  - Generated .py files are valid, executable Python
  - initialize_presets writes the expected files for each Blender version
  - Addon preset data (preset_data_exporters) is importable and valid
  - Addon preset file writing (save_addon_presets)
"""

import ast
import importlib
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Bootstrap: install bpy stubs and the simple_export package stub so that
# relative imports inside the addon resolve without a real Blender process.
# ---------------------------------------------------------------------------

_ADDON_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_EXTENSIONS_ROOT = os.path.dirname(_ADDON_ROOT)

if _EXTENSIONS_ROOT not in sys.path:
    sys.path.insert(0, _EXTENSIONS_ROOT)

# bpy_stub must be imported (and install() called) before any addon module.
from tests.bpy_stub import install as _install_bpy, make_simple_export_package

_install_bpy(blender_version=(5, 1, 0))
make_simple_export_package()

# Now we can safely import the preset subpackages.
import simple_export.presets_export as _pe

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Keys every FBX preset must contain.
_REQUIRED_FBX_KEYS = {
    "filepath", "use_selection", "use_visible", "use_active_collection",
    "global_scale", "apply_unit_scale", "apply_scale_options",
    "object_types", "use_mesh_modifiers", "mesh_smooth_type",
    "bake_anim", "path_mode", "batch_mode", "axis_forward", "axis_up",
}

# Keys every GLTF preset must contain.
_REQUIRED_GLTF_KEYS = {
    "filepath", "export_format", "export_texcoords", "export_normals",
    "export_materials", "export_animations", "export_skins",
    "export_yup", "export_apply",
}

# Keys every addon workflow preset must contain.
_REQUIRED_ADDON_KEYS = {
    "export_format", "export_folder_mode", "folder_path_relative",
    "filename_prefix", "filename_suffix", "set_export_path",
    "assign_preset",
}

# (module_path, variable_name) for all version-specific preset modules.
_PRESET_MODULES = [
    ("simple_export.presets_export.blender_4x.preset_data_fbx", "presets_fbx"),
    ("simple_export.presets_export.blender_4x.preset_data_gltf", "presets_gltf"),
    ("simple_export.presets_export.blender_5_0.preset_data_fbx", "presets_fbx"),
    ("simple_export.presets_export.blender_5_0.preset_data_gltf", "presets_gltf"),
    ("simple_export.presets_export.blender_5_1.preset_data_fbx", "presets_fbx"),
    ("simple_export.presets_export.blender_5_1.preset_data_gltf", "presets_gltf"),
]

_EXPECTED_FBX_PRESETS = {"UE-fbx", "Unity-fbx", "Lowpoly-fbx", "Highpoly-fbx"}
_EXPECTED_GLTF_PRESETS = {"Godot-gltf"}
_EXPECTED_ADDON_PRESETS = {
    "UE-default", "Unity-default", "Godot-default", "Lowpoly-default", "Highpoly-default"
}


# ---------------------------------------------------------------------------
# 1. Version routing
# ---------------------------------------------------------------------------

class TestVersionRouting(unittest.TestCase):
    """get_versioned_module must map Blender versions to the correct subpackage."""

    def _route(self, version, preset_type="fbx"):
        return _pe.get_versioned_module(version, preset_type)

    # -- Blender 4.x --
    def test_4_2_routes_to_4x_fbx(self):
        self.assertEqual(self._route((4, 2, 0)), ".blender_4x.preset_data_fbx")

    def test_4_9_routes_to_4x_fbx(self):
        self.assertEqual(self._route((4, 9, 0)), ".blender_4x.preset_data_fbx")

    def test_4_2_routes_to_4x_gltf(self):
        self.assertEqual(self._route((4, 2, 0), "gltf"), ".blender_4x.preset_data_gltf")

    # -- Blender 5.0 --
    def test_5_0_routes_to_5_0_fbx(self):
        self.assertEqual(self._route((5, 0, 0)), ".blender_5_0.preset_data_fbx")

    def test_5_0_routes_to_5_0_gltf(self):
        self.assertEqual(self._route((5, 0, 0), "gltf"), ".blender_5_0.preset_data_gltf")

    # -- Blender 5.1 --
    def test_5_1_routes_to_5_1_fbx(self):
        self.assertEqual(self._route((5, 1, 0)), ".blender_5_1.preset_data_fbx")

    def test_5_1_routes_to_5_1_gltf(self):
        self.assertEqual(self._route((5, 1, 0), "gltf"), ".blender_5_1.preset_data_gltf")

    # -- Future Blender 5.x falls through to latest known (5.1) --
    def test_5_2_routes_to_5_1_fbx(self):
        self.assertEqual(self._route((5, 2, 0)), ".blender_5_1.preset_data_fbx")

    def test_5_9_routes_to_5_1_gltf(self):
        self.assertEqual(self._route((5, 9, 0), "gltf"), ".blender_5_1.preset_data_gltf")


# ---------------------------------------------------------------------------
# 2. Preset module importability
# ---------------------------------------------------------------------------

class TestPresetModuleImports(unittest.TestCase):
    """Every versioned preset module must be importable and expose the right dict."""

    def _load(self, module_path, var_name):
        mod = importlib.import_module(module_path)
        self.assertTrue(
            hasattr(mod, var_name),
            f"{module_path} is missing '{var_name}'",
        )
        data = getattr(mod, var_name)
        self.assertIsInstance(data, dict, f"{module_path}.{var_name} must be a dict")
        return data

    def test_blender_4x_fbx_importable(self):
        self._load("simple_export.presets_export.blender_4x.preset_data_fbx", "presets_fbx")

    def test_blender_4x_gltf_importable(self):
        self._load("simple_export.presets_export.blender_4x.preset_data_gltf", "presets_gltf")

    def test_blender_5_0_fbx_importable(self):
        self._load("simple_export.presets_export.blender_5_0.preset_data_fbx", "presets_fbx")

    def test_blender_5_0_gltf_importable(self):
        self._load("simple_export.presets_export.blender_5_0.preset_data_gltf", "presets_gltf")

    def test_blender_5_1_fbx_importable(self):
        self._load("simple_export.presets_export.blender_5_1.preset_data_fbx", "presets_fbx")

    def test_blender_5_1_gltf_importable(self):
        self._load("simple_export.presets_export.blender_5_1.preset_data_gltf", "presets_gltf")


# ---------------------------------------------------------------------------
# 3. Preset data completeness
# ---------------------------------------------------------------------------

class TestPresetDataCompleteness(unittest.TestCase):
    """Every versioned preset must contain all expected preset names and required keys."""

    def _fbx_data(self, version_folder):
        mod = importlib.import_module(
            f"simple_export.presets_export.{version_folder}.preset_data_fbx"
        )
        return mod.presets_fbx

    def _gltf_data(self, version_folder):
        mod = importlib.import_module(
            f"simple_export.presets_export.{version_folder}.preset_data_gltf"
        )
        return mod.presets_gltf

    def _assert_fbx_presets_valid(self, data, version_folder):
        missing_presets = _EXPECTED_FBX_PRESETS - data.keys()
        self.assertFalse(
            missing_presets,
            f"{version_folder}: missing FBX presets: {missing_presets}",
        )
        for preset_name, preset in data.items():
            missing_keys = _REQUIRED_FBX_KEYS - preset.keys()
            self.assertFalse(
                missing_keys,
                f"{version_folder}/{preset_name}: missing keys: {missing_keys}",
            )
            self.assertIsInstance(
                preset["object_types"], set,
                f"{version_folder}/{preset_name}: 'object_types' must be a set",
            )
            self.assertIsInstance(
                preset["global_scale"], float,
                f"{version_folder}/{preset_name}: 'global_scale' must be a float",
            )
            self.assertIsInstance(
                preset["bake_anim"], bool,
                f"{version_folder}/{preset_name}: 'bake_anim' must be a bool",
            )

    def _assert_gltf_presets_valid(self, data, version_folder):
        missing_presets = _EXPECTED_GLTF_PRESETS - data.keys()
        self.assertFalse(
            missing_presets,
            f"{version_folder}: missing GLTF presets: {missing_presets}",
        )
        for preset_name, preset in data.items():
            missing_keys = _REQUIRED_GLTF_KEYS - preset.keys()
            self.assertFalse(
                missing_keys,
                f"{version_folder}/{preset_name}: missing keys: {missing_keys}",
            )

    def test_blender_4x_fbx_complete(self):
        self._assert_fbx_presets_valid(self._fbx_data("blender_4x"), "blender_4x")

    def test_blender_4x_gltf_complete(self):
        self._assert_gltf_presets_valid(self._gltf_data("blender_4x"), "blender_4x")

    def test_blender_5_0_fbx_complete(self):
        self._assert_fbx_presets_valid(self._fbx_data("blender_5_0"), "blender_5_0")

    def test_blender_5_0_gltf_complete(self):
        self._assert_gltf_presets_valid(self._gltf_data("blender_5_0"), "blender_5_0")

    def test_blender_5_1_fbx_complete(self):
        self._assert_fbx_presets_valid(self._fbx_data("blender_5_1"), "blender_5_1")

    def test_blender_5_1_gltf_complete(self):
        self._assert_gltf_presets_valid(self._gltf_data("blender_5_1"), "blender_5_1")


# ---------------------------------------------------------------------------
# 4. Generated preset file validity
# ---------------------------------------------------------------------------

class TestGeneratedPresetFiles(unittest.TestCase):
    """save_export_presets must write syntactically valid, executable Python."""

    def _write_and_read(self, preset_name, preset_data):
        with tempfile.TemporaryDirectory() as tmpdir:
            _pe.save_export_presets(preset_name, tmpdir, preset_data)
            out_path = os.path.join(tmpdir, f"{preset_name}.py")
            self.assertTrue(
                os.path.exists(out_path),
                f"Preset file not created: {out_path}",
            )
            with open(out_path, encoding="utf-8") as fh:
                return fh.read()

    def _assert_valid_python(self, source, label):
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            self.fail(f"{label}: generated file has syntax error: {exc}\n\n{source}")
        return tree

    def _assert_has_assignments(self, source, required_keys, label):
        for key in required_keys:
            self.assertIn(
                f"op.{key} =",
                source,
                f"{label}: generated file missing assignment for '{key}'",
            )

    def _test_fbx_preset(self, version_folder, preset_name):
        mod = importlib.import_module(
            f"simple_export.presets_export.{version_folder}.preset_data_fbx"
        )
        preset = mod.presets_fbx[preset_name]
        source = self._write_and_read(preset_name, preset)
        label = f"{version_folder}/{preset_name}"
        self._assert_valid_python(source, label)
        self._assert_has_assignments(source, _REQUIRED_FBX_KEYS - {"filepath"}, label)

    def _test_gltf_preset(self, version_folder, preset_name):
        mod = importlib.import_module(
            f"simple_export.presets_export.{version_folder}.preset_data_gltf"
        )
        preset = mod.presets_gltf[preset_name]
        source = self._write_and_read(preset_name, preset)
        label = f"{version_folder}/{preset_name}"
        self._assert_valid_python(source, label)
        self._assert_has_assignments(source, _REQUIRED_GLTF_KEYS - {"filepath"}, label)

    # -- FBX --
    def test_blender_4x_ue_fbx_valid(self):
        self._test_fbx_preset("blender_4x", "UE-fbx")

    def test_blender_4x_unity_fbx_valid(self):
        self._test_fbx_preset("blender_4x", "Unity-fbx")

    def test_blender_5_0_ue_fbx_valid(self):
        self._test_fbx_preset("blender_5_0", "UE-fbx")

    def test_blender_5_1_ue_fbx_valid(self):
        self._test_fbx_preset("blender_5_1", "UE-fbx")

    def test_blender_5_1_lowpoly_fbx_valid(self):
        self._test_fbx_preset("blender_5_1", "Lowpoly-fbx")

    def test_blender_5_1_highpoly_fbx_valid(self):
        self._test_fbx_preset("blender_5_1", "Highpoly-fbx")

    # -- GLTF --
    def test_blender_4x_godot_gltf_valid(self):
        self._test_gltf_preset("blender_4x", "Godot-gltf")

    def test_blender_5_0_godot_gltf_valid(self):
        self._test_gltf_preset("blender_5_0", "Godot-gltf")

    def test_blender_5_1_godot_gltf_valid(self):
        self._test_gltf_preset("blender_5_1", "Godot-gltf")

    def test_set_values_are_valid_python_literals(self):
        """object_types (a set) must round-trip through the generated file."""
        from simple_export.presets_export.blender_5_1.preset_data_fbx import presets_fbx
        preset = presets_fbx["UE-fbx"]
        source = self._write_and_read("UE-fbx", preset)
        # ast.literal_eval requires a pure literal; extract just the set assignment
        for line in source.splitlines():
            if "op.object_types" in line:
                _, _, rhs = line.partition("= ")
                try:
                    value = ast.literal_eval(rhs.strip())
                    self.assertIsInstance(value, (set, frozenset))
                except (ValueError, SyntaxError) as exc:
                    self.fail(f"object_types value is not a valid literal: {exc}\nLine: {line}")
                break
        else:
            self.fail("No object_types assignment found in generated file")


# ---------------------------------------------------------------------------
# 5. initialize_presets integration
# ---------------------------------------------------------------------------

class TestInitializePresets(unittest.TestCase):
    """initialize_presets must write the correct files for each Blender version."""

    def _run_initialize(self, blender_version):
        with tempfile.TemporaryDirectory() as tmpdir:
            fbx_dir = os.path.join(tmpdir, "export_scene.fbx")
            gltf_dir = os.path.join(tmpdir, "export_scene.gltf")
            os.makedirs(fbx_dir)
            os.makedirs(gltf_dir)

            with (
                patch.object(_pe, "get_fbx_presets_folder", return_value=fbx_dir),
                patch.object(_pe, "get_gltf_presets_folder", return_value=gltf_dir),
                patch.object(_pe, "get_blender_version", return_value=blender_version),
            ):
                _pe.initialize_presets()

            return set(os.listdir(fbx_dir)), set(os.listdir(gltf_dir))

    def _assert_preset_files(self, fbx_files, gltf_files, label):
        expected_fbx = {f"{n}.py" for n in _EXPECTED_FBX_PRESETS}
        expected_gltf = {f"{n}.py" for n in _EXPECTED_GLTF_PRESETS}

        missing_fbx = expected_fbx - fbx_files
        missing_gltf = expected_gltf - gltf_files
        self.assertFalse(missing_fbx, f"{label}: FBX preset files not created: {missing_fbx}")
        self.assertFalse(missing_gltf, f"{label}: GLTF preset files not created: {missing_gltf}")

    def test_blender_4x_creates_all_preset_files(self):
        fbx, gltf = self._run_initialize((4, 2, 0))
        self._assert_preset_files(fbx, gltf, "Blender 4.2")

    def test_blender_5_0_creates_all_preset_files(self):
        fbx, gltf = self._run_initialize((5, 0, 0))
        self._assert_preset_files(fbx, gltf, "Blender 5.0")

    def test_blender_5_1_creates_all_preset_files(self):
        fbx, gltf = self._run_initialize((5, 1, 0))
        self._assert_preset_files(fbx, gltf, "Blender 5.1")

    def test_existing_files_are_not_overwritten(self):
        """Preset files that already exist must not be re-written."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fbx_dir = os.path.join(tmpdir, "export_scene.fbx")
            gltf_dir = os.path.join(tmpdir, "export_scene.gltf")
            os.makedirs(fbx_dir)
            os.makedirs(gltf_dir)

            # Pre-populate UE-fbx.py with sentinel content
            sentinel = "# sentinel\n"
            ue_path = os.path.join(fbx_dir, "UE-fbx.py")
            with open(ue_path, "w") as fh:
                fh.write(sentinel)

            with (
                patch.object(_pe, "get_fbx_presets_folder", return_value=fbx_dir),
                patch.object(_pe, "get_gltf_presets_folder", return_value=gltf_dir),
                patch.object(_pe, "get_blender_version", return_value=(5, 1, 0)),
            ):
                _pe.initialize_presets()

            with open(ue_path) as fh:
                content = fh.read()
            self.assertEqual(content, sentinel, "Existing preset file was overwritten")

    def test_generated_files_are_valid_python(self):
        """All files written by initialize_presets must be parseable Python."""
        with tempfile.TemporaryDirectory() as tmpdir:
            fbx_dir = os.path.join(tmpdir, "export_scene.fbx")
            gltf_dir = os.path.join(tmpdir, "export_scene.gltf")
            os.makedirs(fbx_dir)
            os.makedirs(gltf_dir)

            with (
                patch.object(_pe, "get_fbx_presets_folder", return_value=fbx_dir),
                patch.object(_pe, "get_gltf_presets_folder", return_value=gltf_dir),
                patch.object(_pe, "get_blender_version", return_value=(5, 1, 0)),
            ):
                _pe.initialize_presets()

            for folder in (fbx_dir, gltf_dir):
                for fname in os.listdir(folder):
                    fpath = os.path.join(folder, fname)
                    with open(fpath) as fh:
                        source = fh.read()
                    try:
                        ast.parse(source)
                    except SyntaxError as exc:
                        self.fail(f"{fname}: syntax error in generated preset: {exc}")


# ---------------------------------------------------------------------------
# 6. Addon preset data (preset_data_exporters)
# ---------------------------------------------------------------------------

class TestAddonPresetData(unittest.TestCase):
    """preset_data_exporters must be importable and contain complete workflow presets."""

    @classmethod
    def setUpClass(cls):
        # Import the addon preset data (requires bpy stubs already installed)
        cls.mod = importlib.import_module(
            "simple_export.presets_addon.preset_data_exporters"
        )
        cls.data = cls.mod.presets_simple_exporter

    def test_is_dict(self):
        self.assertIsInstance(self.data, dict)

    def test_expected_workflow_presets_present(self):
        missing = _EXPECTED_ADDON_PRESETS - self.data.keys()
        self.assertFalse(missing, f"Missing workflow presets: {missing}")

    def test_all_presets_have_required_keys(self):
        for name, preset in self.data.items():
            missing = _REQUIRED_ADDON_KEYS - preset.keys()
            self.assertFalse(missing, f"'{name}' missing keys: {missing}")

    def test_export_format_values_are_known(self):
        known_formats = {"FBX", "GLTF", "OBJ", "USD", "ABC", "PLY", "STL"}
        for name, preset in self.data.items():
            fmt = preset.get("export_format", "")
            self.assertIn(
                fmt, known_formats,
                f"'{name}' has unknown export_format '{fmt}'",
            )

    def test_fbx_presets_reference_existing_fbx_preset_names(self):
        """FBX workflow presets must reference an FBX exporter preset that exists."""
        from simple_export.presets_export.blender_5_1.preset_data_fbx import presets_fbx
        known_fbx = {f"{n}.py" for n in presets_fbx}
        for name, preset in self.data.items():
            if preset.get("export_format") != "FBX":
                continue
            ref = preset.get("simple_export_preset_file_fbx", "")
            filename = os.path.basename(ref)
            self.assertIn(
                filename, known_fbx,
                f"'{name}' references unknown FBX preset '{filename}'",
            )

    def test_gltf_presets_reference_existing_gltf_preset_names(self):
        """GLTF workflow presets must reference a GLTF exporter preset that exists."""
        from simple_export.presets_export.blender_5_1.preset_data_gltf import presets_gltf
        known_gltf = {f"{n}.py" for n in presets_gltf}
        for name, preset in self.data.items():
            if preset.get("export_format") != "GLTF":
                continue
            ref = preset.get("simple_export_preset_file_gltf", "")
            filename = os.path.basename(ref)
            self.assertIn(
                filename, known_gltf,
                f"'{name}' references unknown GLTF preset '{filename}'",
            )


# ---------------------------------------------------------------------------
# 7. Addon preset file writing
# ---------------------------------------------------------------------------

class TestAddonPresetFileWriting(unittest.TestCase):
    """save_addon_presets must write valid, complete Python files."""

    def _write(self, preset_name, preset_data):
        from simple_export.presets_addon import save_addon_presets
        with tempfile.TemporaryDirectory() as tmpdir:
            save_addon_presets(preset_name, tmpdir, preset_data)
            path = os.path.join(tmpdir, f"{preset_name}.py")
            self.assertTrue(os.path.exists(path), f"Addon preset file not created: {path}")
            with open(path, encoding="utf-8") as fh:
                return fh.read()

    def _get_preset(self, name):
        mod = importlib.import_module("simple_export.presets_addon.preset_data_exporters")
        return mod.presets_simple_exporter[name]

    def test_ue_default_generates_valid_python(self):
        source = self._write("UE-default", self._get_preset("UE-default"))
        try:
            ast.parse(source)
        except SyntaxError as exc:
            self.fail(f"UE-default: syntax error in generated addon preset: {exc}")

    def test_godot_default_generates_valid_python(self):
        source = self._write("Godot-default", self._get_preset("Godot-default"))
        try:
            ast.parse(source)
        except SyntaxError as exc:
            self.fail(f"Godot-default: syntax error in generated addon preset: {exc}")

    def test_generated_file_contains_scene_assignments(self):
        source = self._write("UE-default", self._get_preset("UE-default"))
        self.assertIn("scene.export_format =", source)
        self.assertIn("scene.export_folder_mode =", source)

    def test_backslash_in_path_is_escaped(self):
        """Windows-style paths in preset values must not break the generated file."""
        preset = {"folder_path_absolute": "C:\\tmp\\export"}
        source = self._write("test-backslash", preset)
        try:
            ast.parse(source)
        except SyntaxError as exc:
            self.fail(f"Backslash escaping failed: {exc}\n{source}")
        self.assertIn("C:\\\\tmp\\\\export", source)


# ---------------------------------------------------------------------------
# 8. Version-specific preset structural guards
# ---------------------------------------------------------------------------

class TestVersionSpecificPresetValues(unittest.TestCase):
    """
    Structural guards for version-specific preset data.

    As of writing, the active FBX and GLTF preset dictionaries are identical
    across blender_4x, blender_5_0, and blender_5_1 (the API parameters have
    not changed yet). These tests therefore focus on structural invariants —
    presence of required keys and consistent preset names — rather than
    value-diff assertions. When a future Blender version introduces API
    differences, update the relevant preset module AND add value assertions here.
    """

    _VERSION_FOLDERS = ["blender_4x", "blender_5_0", "blender_5_1"]

    def _load_fbx(self, version_folder):
        import importlib
        mod = importlib.import_module(
            f"simple_export.presets_export.{version_folder}.preset_data_fbx"
        )
        return mod.presets_fbx

    def test_all_versions_have_same_fbx_preset_names(self):
        """All three version folders must expose the same set of FBX preset names."""
        key_sets = [set(self._load_fbx(v).keys()) for v in self._VERSION_FOLDERS]
        reference = key_sets[0]
        for version_folder, keys in zip(self._VERSION_FOLDERS[1:], key_sets[1:]):
            self.assertEqual(
                keys, reference,
                f"{version_folder} FBX preset names differ from blender_4x: "
                f"added={keys - reference}, removed={reference - keys}",
            )

    def test_ue_fbx_axis_forward_defined_in_all_versions(self):
        """
        UE-fbx must define axis_forward in every version folder.

        Current expected value across all versions: "X".
        If Blender changes the FBX exporter API and this value must differ,
        update this test intentionally and document the reason.
        """
        for version_folder in self._VERSION_FOLDERS:
            with self.subTest(version_folder=version_folder):
                presets = self._load_fbx(version_folder)
                self.assertIn(
                    "axis_forward", presets["UE-fbx"],
                    f"{version_folder}/UE-fbx is missing 'axis_forward'",
                )
                # Record the current value; change this assertion when the API diverges.
                self.assertEqual(
                    presets["UE-fbx"]["axis_forward"], "X",
                    f"{version_folder}/UE-fbx: unexpected axis_forward value",
                )

    def test_blender_4x_fbx_has_exactly_four_presets(self):
        """
        blender_4x defines exactly 4 active FBX presets.

        A commented-out 'Northlight-fbx' entry exists in that module. This test
        guards against accidentally uncommenting it without bumping the expected count.
        """
        presets = self._load_fbx("blender_4x")
        self.assertEqual(
            len(presets), 4,
            f"blender_4x has {len(presets)} FBX presets; expected 4. "
            "If you intentionally added or removed a preset, update this count.",
        )

    def test_preset_dicts_are_independent_objects(self):
        """
        Importing a version module and mutating the returned dict must not affect
        subsequent imports (guards against shared module-level mutable state).
        """
        import importlib
        mod1 = importlib.import_module(
            "simple_export.presets_export.blender_5_1.preset_data_fbx"
        )
        # Make a shallow copy of the original keys before mutating.
        original_keys = set(mod1.presets_fbx.keys())

        # Mutate the dict from the first import.
        sentinel_key = "__test_sentinel__"
        mod1.presets_fbx[sentinel_key] = {}

        # Re-import — Python returns the cached module, so we reload to get a fresh one.
        mod2 = importlib.reload(
            importlib.import_module(
                "simple_export.presets_export.blender_5_1.preset_data_fbx"
            )
        )

        self.assertNotIn(
            sentinel_key, mod2.presets_fbx,
            "Mutating the presets_fbx dict of one import leaked into a reloaded module.",
        )
        self.assertEqual(set(mod2.presets_fbx.keys()), original_keys)


if __name__ == "__main__":
    unittest.main()
