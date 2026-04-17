import bpy

from ..preferences.preferenecs import PROPERTY_METADATA
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
    )

    folder_path_relative: bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_relative"]["name"],
        description=PROPERTY_METADATA["folder_path_relative"]["description"],
        default=PROPERTY_METADATA["folder_path_relative"]["default"],
    )

    folder_path_search: bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_search"]["name"],
        description=PROPERTY_METADATA["folder_path_search"]["description"],
        default=PROPERTY_METADATA["folder_path_search"]["default"]
    )
    folder_path_replace: bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_replace"]["name"],
        description=PROPERTY_METADATA["folder_path_replace"]["description"],
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
from ..preferences.preferenecs import get_py_files_for_fbx, get_py_files_for_obj, get_py_files_for_abc, \
    get_py_files_for_ply, get_py_files_for_stl, get_py_files_for_usd, get_py_files_for_gltf


class SharedFormatProps:
    from ..core.export_formats import get_export_format_items
    export_format: bpy.props.EnumProperty(
        name="Export Format",
        description="Select the export format",
        items=get_export_format_items(),  # Dynamically generated items from EXPORT_FORMATS
    )


class SharedPresetAssignmentProps:
    simple_export_preset_file_fbx: bpy.props.EnumProperty(
        name="FBX Preset File",
        description="Select a preset file for FBX",
        items=lambda self, context: get_py_files_for_fbx(self, context),
    )

    simple_export_preset_file_obj: bpy.props.EnumProperty(
        name="OBJ Preset File",
        description="Select a preset file for OBJ",
        items=lambda self, context: get_py_files_for_obj(self, context),
    )

    simple_export_preset_file_gltf: bpy.props.EnumProperty(
        name="glTF Preset File",
        description="Select a preset file for glTF",
        items=lambda self, context: get_py_files_for_gltf(self, context),
    )

    simple_export_preset_file_usd: bpy.props.EnumProperty(
        name="USD Preset File",
        description="Select a preset file for USD",
        items=lambda self, context: get_py_files_for_usd(self, context),
    )

    simple_export_preset_file_abc: bpy.props.EnumProperty(
        name="Alembic Preset File",
        description="Select a preset file for Alembic",
        items=lambda self, context: get_py_files_for_abc(self, context),
    )

    simple_export_preset_file_ply: bpy.props.EnumProperty(
        name="PLY Preset File",
        description="Select a preset file for PLY",
        items=lambda self, context: get_py_files_for_ply(self, context),
    )

    simple_export_preset_file_stl: bpy.props.EnumProperty(
        name="STL Preset File",
        description="Select a preset file for STL",
        items=lambda self, context: get_py_files_for_stl(self, context),
    )

    assign_preset: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["assign_preset"]["name"],
        description=PROPERTY_METADATA["assign_preset"]["description"],
        default=PROPERTY_METADATA["assign_preset"]["default"]
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

    collection_blend_prefix: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["collection_blend_prefix"]["name"],
        description=PROPERTY_METADATA["collection_blend_prefix"]["description"],
        default=PROPERTY_METADATA["collection_blend_prefix"]["default"]
    )

    # Should they even be here?
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
        name=PROPERTY_METADATA["use_root_object"]["name"],
        description=PROPERTY_METADATA["use_root_object"]["description"],
        default=PROPERTY_METADATA["use_root_object"]["default"]
    )
    collection_instance_offset: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["collection_instance_offset"]["name"],
        description=PROPERTY_METADATA["collection_instance_offset"]["description"],
        default=PROPERTY_METADATA["collection_instance_offset"]["default"]
    )
    create_empty_root: bpy.props.BoolProperty(
        name="Add Root Empty (if missing)",
        description=(
            "Create a new EMPTY object, parent the collection's top-level objects to it, "
            "and assign it as the collection's root object"
        ),
        default=False,
    )

    root_empty_suffix: bpy.props.StringProperty(
        name="Root Empty Suffix",
        description="Suffix appended to the collection name when naming the root empty object",
        default="_root",
    )


class CollectionPreExportProps:
    move_by_collection_offset: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["move_by_collection_offset"]["name"],
        description=PROPERTY_METADATA["move_by_collection_offset"]["description"],
        default=PROPERTY_METADATA["move_by_collection_offset"]["default"],
    )
    triangulate_before_export: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["triangulate_before_export"]["name"],
        description=PROPERTY_METADATA["triangulate_before_export"]["description"],
        default=PROPERTY_METADATA["triangulate_before_export"]["default"],
    )
    triangulate_keep_normals: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["triangulate_keep_normals"]["name"],
        description=PROPERTY_METADATA["triangulate_keep_normals"]["description"],
        default=PROPERTY_METADATA["triangulate_keep_normals"]["default"],
    )
    apply_scale_before_export: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["apply_scale_before_export"]["name"],
        description=PROPERTY_METADATA["apply_scale_before_export"]["description"],
        default=PROPERTY_METADATA["apply_scale_before_export"]["default"],
    )
    apply_rotation_before_export: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["apply_rotation_before_export"]["name"],
        description=PROPERTY_METADATA["apply_rotation_before_export"]["description"],
        default=PROPERTY_METADATA["apply_rotation_before_export"]["default"],
    )
    apply_transform_before_export: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["apply_transform_before_export"]["name"],
        description=PROPERTY_METADATA["apply_transform_before_export"]["description"],
        default=PROPERTY_METADATA["apply_transform_before_export"]["default"],
    )
    pre_rotate_objects: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["pre_rotate_objects"]["name"],
        description=PROPERTY_METADATA["pre_rotate_objects"]["description"],
        default=PROPERTY_METADATA["pre_rotate_objects"]["default"],
    )


class CollectionSettingsProps:
    collection_color: bpy.props.EnumProperty(
        name=PROPERTY_METADATA["collection_color"]["name"],
        description=PROPERTY_METADATA["collection_color"]["description"],
        items=PROPERTY_METADATA["collection_color"]["items"],
        default=PROPERTY_METADATA["collection_color"]["default"],
    )
    parent_collection: bpy.props.StringProperty(
        name="Parent Collection",
        description="Name of the parent collection for the collection",
        default=""
    )
