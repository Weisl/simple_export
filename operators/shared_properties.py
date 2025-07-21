import bpy

from ..preferences.preferenecs import PROPERTY_METADATA


# --- Property Getter/Setter Functions ---
def get_relative_path(self):
    stored_path = self.get("folder_path_relative", "")
    if not stored_path:
        return ""
    if stored_path.startswith("//"):
        return stored_path
    rel = bpy.path.relpath(stored_path)
    if rel.startswith("//"):
        return rel
    return stored_path


def set_relative_path(self, value):
    if not value:
        self["folder_path_relative"] = ""
        return
    rel = bpy.path.relpath(value)
    if rel.startswith("//"):
        self["folder_path_relative"] = rel
    else:
        self["folder_path_relative"] = bpy.path.abspath(value)


def get_absolute_path(self):
    stored_path = self.get("folder_path_absolute", "")
    return bpy.path.abspath(stored_path) if stored_path else ""


def set_absolute_path(self, value):
    self["folder_path_absolute"] = bpy.path.abspath(value) if value else ""


# --- Shared Property Classes ---

class SharedPathProps:
    export_folder_mode: bpy.props.EnumProperty(
        name="Export Path Mode",
        description="Choose how the export folder is determined",
        items=[
            ('RELATIVE', "Relative", "Use a path relative to the blend file"),
            ('ABSOLUTE', "Absolute", "Use an absolute path"),
            ('MIRROR', "Mirror", "Mirror a source path to a target path"),
        ],
        default='RELATIVE',
    )
    folder_path_absolute: bpy.props.StringProperty(
        name="Absolute Folder Path",
        description="Absolute folder path for export",
        subtype='DIR_PATH',
        default="",
        get=get_absolute_path,
        set=set_absolute_path
    )
    folder_path_relative: bpy.props.StringProperty(
        name="Relative Folder Path",
        description="Relative folder path for export",
        subtype='DIR_PATH',
        default="//.",
        get=get_relative_path,
        set=set_relative_path
    )
    folder_path_search: bpy.props.StringProperty(
        name="Search Path",
        description="Path to search for mirroring",
        subtype='DIR_PATH',
        default=""
    )
    folder_path_replace: bpy.props.StringProperty(
        name="Replacement Path",
        description="Replacement path for mirroring",
        subtype='DIR_PATH',
        default=""
    )


class SharedFilenameProps:
    filename_prefix: bpy.props.StringProperty(
        name="Filename  Prefix",
        description="Custom prefix for filenames",
        default=""
    )
    filename_suffix: bpy.props.StringProperty(
        name="Filename Suffix",
        description="Custom suffix for filenames",
        default=""
    )
    filename_blend_prefix: bpy.props.BoolProperty(
        name="Append Blend name to Filename",
        description="Use the blend file name as prefix for filenames",
        default=False
    )


class SharedPathAssignmentProps:
    assign_export_filepath: bpy.props.BoolProperty(
        name="Assign Export Folder",
        description="Assign the export folder to the exporter",
        default=True
    )
    export_filepath: bpy.props.StringProperty(
        name="Folder",
        description="Filepath for the export",
        default="",
        subtype='DIR_PATH'
    )


class SharedPresetAssignmentProps:
    preset_filepath: bpy.props.StringProperty(
        name="Preset Path",
        description="Path to the preset file to assign to the exporter",
        default="",
        subtype='FILE_PATH'
    )
    assign_preset: bpy.props.BoolProperty(
        name="Assign Preset",
        description="Assign the preset to the exporter",
        default=True
    )


class CollectionNamingProps:
    collection_suffix: bpy.props.StringProperty(
        name="Custom Suffix",
        description="Custom suffix for collection names",
        default=""
    )
    collection_prefix: bpy.props.StringProperty(
        name="Custom Prefix",
        description="Custom prefix for collection names",
        default=""
    )
    collection_name_new: bpy.props.StringProperty(
        name="Name",
        description="Overwrite the name for the collection",
        default=""
    )
    collection_naming_overwrite: bpy.props.BoolProperty(
        name="Overwrite Naming",
        description="Overwrite the naming for the collection",
        default=False
    )


class CollectionOriginProps:
    use_root_object: bpy.props.BoolProperty(
        name="Use Root Object",
        description="Use a root object for the collection",
        default=True
    )
    collection_instance_offset: bpy.props.BoolProperty(
        name="Set Instance Offset",
        description="Set instance offset for the collection",
        default=False
    )


class CollectionSettingsProps:
    collection_color: bpy.props.EnumProperty(
        name=PROPERTY_METADATA["collection_color"]["name"],
        description=PROPERTY_METADATA["collection_color"]["description"],
        items=PROPERTY_METADATA["collection_color"]["items"],
        default=PROPERTY_METADATA["collection_color"]["default"],
    )
    parent_collection_name: bpy.props.StringProperty(
        name="Parent Collection",
        description="Name of the parent collection for the collection",
        default=""
    )
