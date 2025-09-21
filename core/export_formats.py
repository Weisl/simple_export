import os


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
        from ..presets_export.preset_format_functions import get_preset_format_folder
        return os.path.join(get_preset_format_folder(), self.preset_subfolder)

    def __repr__(self):
        return f"<ExportFormat {self.label} ({self.file_extension})>"


class ExportFormats:
    """Manages and provides access to export formats."""
    FORMATS = {
        "FBX": ExportFormat("FBX", "IO_FH_fbx", "FBX", "FBX Export", "export_scene.fbx",
                            "<class 'bpy.types.EXPORT_SCENE_OT_fbx'>", "fbx"),
        "OBJ": ExportFormat("OBJ", "IO_FH_obj", "OBJ", "Wavefront OBJ Export", "wm.obj_export",
                            "<class 'bpy.types.WM_OT_obj_export'>", "obj"),
        "GLTF": ExportFormat("GLTF", "IO_FH_gltf2", "glTF 2.0", "glTF 2.0 Export", "export_scene.gltf",
                                      "<class 'bpy.types.EXPORT_SCENE_OT_gltf'>", "gltf"),
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

    @classmethod
    def get_key_from_op_type(cls, op_type):
        """Retrieve the key (e.g., 'FBX') from an op_type string."""
        for key, fmt in cls.FORMATS.items():
            if fmt.op_type == op_type:
                return key
        return None


def get_export_format_items():
    """Return a list of export formats for UI dropdowns."""
    return [(key, fmt.label, fmt.description) for key, fmt in ExportFormats.FORMATS.items()]
