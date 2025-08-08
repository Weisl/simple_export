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
        name=PROPERTY_METADATA["export_folder_mode"]["name"],
        description=PROPERTY_METADATA["export_folder_mode"]["description"],
        items=PROPERTY_METADATA["export_folder_mode"]["items"],
        default=PROPERTY_METADATA["export_folder_mode"]["default"],
    )
    folder_path_absolute: bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_absolute"]["name"],
        description=PROPERTY_METADATA["folder_path_absolute"]["description"],
        subtype='DIR_PATH',
        default=PROPERTY_METADATA["folder_path_absolute"]["default"],
        get=get_absolute_path,
        set=set_absolute_path
    )
    folder_path_relative: bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_relative"]["name"],
        description=PROPERTY_METADATA["folder_path_relative"]["description"],
        subtype='DIR_PATH',
        default=PROPERTY_METADATA["folder_path_relative"]["default"],
        get=get_relative_path,
        set=set_relative_path
    )
    folder_path_search: bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_search"]["name"],
        description=PROPERTY_METADATA["folder_path_search"]["description"],
        subtype='DIR_PATH',
        default=PROPERTY_METADATA["folder_path_search"]["default"]
    )
    folder_path_replace: bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_replace"]["name"],
        description=PROPERTY_METADATA["folder_path_replace"]["description"],
        subtype='DIR_PATH',
        default=PROPERTY_METADATA["folder_path_replace"]["default"]
    )


class SharedFilenameProps:
    filename_prefix: bpy.props.StringProperty(
        name=PROPERTY_METADATA["filename_prefix"]["name"],
        description=PROPERTY_METADATA["filename_prefix"]["description"],
        default=PROPERTY_METADATA["filename_prefix"]["default"]
    )
    filename_suffix: bpy.props.StringProperty(
        name=PROPERTY_METADATA["filename_suffix"]["name"],
        description=PROPERTY_METADATA["filename_suffix"]["description"],
        default=PROPERTY_METADATA["filename_suffix"]["default"]
    )
    filename_blend_prefix: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["filename_blend_prefix"]["name"],
        description=PROPERTY_METADATA["filename_blend_prefix"]["description"],
        default=PROPERTY_METADATA["filename_blend_prefix"]["default"]
    )


# Set Folder Path
class SharedPathAssignmentProps:
    set_export_path: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["set_export_path"]["name"],
        description=PROPERTY_METADATA["set_export_path"]["description"],
        default=PROPERTY_METADATA["set_export_path"]["default"]
    )


# Set Presets
from ..preferences.preferenecs import get_py_files_for_fbx, update_preset_path_for_fbx, get_py_files_for_obj, \
    update_preset_path_for_obj, get_py_files_for_abc, get_py_files_for_ply, get_py_files_for_stl, get_py_files_for_usd, \
    get_py_files_for_gltf, update_preset_path_for_gltf, update_preset_path_for_abc, update_preset_path_for_ply, \
    update_preset_path_for_stl, update_preset_path_for_usd


class SharedPresetAssignmentProps:
    simple_export_preset_file_fbx: bpy.props.EnumProperty(
        name="FBX Preset File",
        description="Select a preset file for FBX",
        items=lambda self, context: get_py_files_for_fbx(self, context),
        update=update_preset_path_for_fbx,
    )

    simple_export_preset_file_obj: bpy.props.EnumProperty(
        name="OBJ Preset File",
        description="Select a preset file for OBJ",
        items=lambda self, context: get_py_files_for_obj(self, context),
        update=update_preset_path_for_obj,
    )

    simple_export_preset_file_gltf: bpy.props.EnumProperty(
        name="glTF Preset File",
        description="Select a preset file for glTF",
        items=lambda self, context: get_py_files_for_gltf(self, context),
        update=update_preset_path_for_gltf,
    )

    simple_export_preset_file_usd: bpy.props.EnumProperty(
        name="USD Preset File",
        description="Select a preset file for USD",
        items=lambda self, context: get_py_files_for_usd(self, context),
        update=update_preset_path_for_usd,
    )

    simple_export_preset_file_abc: bpy.props.EnumProperty(
        name="Alembic Preset File",
        description="Select a preset file for Alembic",
        items=lambda self, context: get_py_files_for_abc(self, context),
        update=update_preset_path_for_abc,
    )

    simple_export_preset_file_ply: bpy.props.EnumProperty(
        name="PLY Preset File",
        description="Select a preset file for PLY",
        items=lambda self, context: get_py_files_for_ply(self, context),
        update=update_preset_path_for_ply,
    )

    simple_export_preset_file_stl: bpy.props.EnumProperty(
        name="STL Preset File",
        description="Select a preset file for STL",
        items=lambda self, context: get_py_files_for_stl(self, context),
        update=update_preset_path_for_stl,
    )

    preset_filepath: bpy.props.StringProperty(
        name="Preset Path",
        description="Path to the preset file to assign to the exporter",
        default="",
        subtype='FILE_PATH'
    )
    set_preset: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["set_preset"]["name"],
        description=PROPERTY_METADATA["set_preset"]["description"],
        default=PROPERTY_METADATA["set_preset"]["default"]
    )


class CollectionNamingProps:
    collection_prefix: bpy.props.StringProperty(
        name=PROPERTY_METADATA["collection_prefix"]["name"],
        description=PROPERTY_METADATA["collection_prefix"]["description"],
        default=PROPERTY_METADATA["collection_prefix"]["default"]
    )

    collection_suffix: bpy.props.StringProperty(
        name=PROPERTY_METADATA["collection_suffix"]["name"],
        description=PROPERTY_METADATA["collection_suffix"]["description"],
        default=PROPERTY_METADATA["collection_suffix"]["default"]
    )

    collection_name_new: bpy.props.StringProperty(
        name="Name",
        description="Overwrite the name for the collection",
        default=""
    )

    collection_blend_prefix: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["collection_blend_prefix"]["name"],
        description=PROPERTY_METADATA["collection_blend_prefix"]["description"],
        default=PROPERTY_METADATA["collection_blend_prefix"]["default"]
    )

    #
    collection_naming_overwrite: bpy.props.BoolProperty(
        name="Overwrite Naming",
        description="Overwrite the naming for the collection",
        default=False
    )


class CollectionOriginProps:
    use_root_object: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["use_root_object"]["name"],
        description=PROPERTY_METADATA["use_root_object"]["description"],
        default=PROPERTY_METADATA["use_root_object"]["default"]
    )
    collection_instance_offset: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["collection_instance_offset"]["name"],
        description=PROPERTY_METADATA["collection_instance_offset"]["description"],
        default=PROPERTY_METADATA["collection_instance_offset"]["default"]
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
