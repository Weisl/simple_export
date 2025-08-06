import bpy
import os

from .. import __package__ as base_package


def get_presets_folder():
    """Retrieve the preset folder, using override if set, else default to Blender's location."""
    prefs = bpy.context.preferences.addons[base_package].preferences

    if prefs.preset_path_override and os.path.isdir(prefs.preset_path_override):
        return prefs.preset_path_override

    # Default Blender location
    return os.path.join(bpy.utils.resource_path('USER'), "scripts", "presets_export", "operator")


class ExportFormat:
    """Represents a single export format with its metadata."""

    def __init__(self, key, op_name, label, description, preset_subfolder, op_type, file_extension):
        self.key = key
        self.op_name = op_name
        self.label = label
        self.description = description
        self.preset_subfolder = preset_subfolder  # Store only subfolder name
        self.op_type = op_type
        self.file_extension = file_extension

    @property
    def preset_folder(self):
        """Dynamically retrieve the preset folder when accessed."""
        return os.path.join(get_presets_folder(), self.preset_subfolder)

    def __repr__(self):
        return f"<ExportFormat {self.label} ({self.file_extension})>"


class ExportFormats:
    """Manages and provides access to export formats."""
    FORMATS = {
        "FBX": ExportFormat("FBX", "IO_FH_fbx", "FBX", "FBX Export", "export_scene.fbx",
                            "<class 'bpy.types.EXPORT_SCENE_OT_fbx'>", "fbx"),
        "OBJ": ExportFormat("OBJ", "IO_FH_obj", "OBJ", "Wavefront OBJ Export", "wm.obj_export",
                            "<class 'bpy.types.WM_OT_obj_export'>", "obj"),
        "GLTF": ExportFormat("GLTF", "IO_FH_gltf2", "glTF", "glTF 2.0 Export", "export_scene.gltf",
                             "<class 'bpy.types.EXPORT_SCENE_OT_gltf'>", "glb"),
        "USD": ExportFormat("USD", "IO_FH_usd", "USD", "Universal Scene Description Export", "wm.usd_export",
                            "<class 'bpy.types.WM_OT_usd_export'>", "usd"),
        "ABC": ExportFormat("ABC", "IO_FH_alembic", "Alembic", "Alembic Export", "wm.alembic_export",
                            "<class 'bpy.types.WM_OT_alembic_export'>", "abc"),
        "PLY": ExportFormat("PLY", "IO_FH_ply", "PLY", "Stanford PLY Export", "wm.ply_export",
                            "<class 'bpy.types.WM_OT_ply_export'>", "ply"),
        "STL": ExportFormat("STL", "IO_FH_stl", "STL", "STL Export", "wm.stl_export",
                            "<class 'bpy.types.WM_OT_stl_export'>", "stl"),
    }

    @classmethod
    def get(cls, format_name):
        """Retrieve an export format by its key (e.g., 'FBX')."""
        return cls.FORMATS.get(format_name)

    @classmethod
    def all(cls):
        """Return all export formats as a list."""
        return list(cls.FORMATS.values())


def get_export_format_items():
    """Return a list of export formats for UI dropdowns."""
    return [(key, fmt.label, fmt.description) for key, fmt in ExportFormats.FORMATS.items()]
