import bpy

# --- Property Getter/Setter Functions ---
def get_relative_path(self):
    stored_path = self.get("relative_export_path", "")
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
        self["relative_export_path"] = ""
        return
    rel = bpy.path.relpath(value)
    if rel.startswith("//"):
        self["relative_export_path"] = rel
    else:
        self["relative_export_path"] = bpy.path.abspath(value)

def get_absolute_path(self):
    stored_path = self.get("absolute_export_path", "")
    return bpy.path.abspath(stored_path) if stored_path else ""

def set_absolute_path(self, value):
    self["absolute_export_path"] = bpy.path.abspath(value) if value else ""

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
    absolute_export_path: bpy.props.StringProperty(
        name="Absolute Export Path",
        description="Absolute path for export",
        subtype='DIR_PATH',
        default="",
        get=get_absolute_path,
        set=set_absolute_path
    )
    relative_export_path: bpy.props.StringProperty(
        name="Relative Export Path",
        description="Relative path for export",
        subtype='DIR_PATH',
        default="//.",
        get=get_relative_path,
        set=set_relative_path
    )
    mirror_search_path: bpy.props.StringProperty(
        name="Search Path",
        description="Path to search for mirroring",
        subtype='DIR_PATH',
        default=""
    )
    mirror_replacement_path: bpy.props.StringProperty(
        name="Replacement Path",
        description="Replacement path for mirroring",
        subtype='DIR_PATH',
        default=""
    )

class SharedFilenameProps:
    filename_custom_prefix: bpy.props.StringProperty(
        name="File  Prefix",
        description="Custom prefix for filenames",
        default=""
    )
    filename_custom_suffix: bpy.props.StringProperty(
        name="File Suffix", 
        description="Custom suffix for filenames",
        default=""
    )
    filename_file_name_prefix: bpy.props.BoolProperty(
        name="Use File Name as Prefix",
        description="Use the blend file name as prefix for filenames",
        default=False
    )

# --- Grouped Property Mixins ---
class FilepathAssignmentProps:
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

class PresetProps:
    preset_filepath: bpy.props.StringProperty(
        name="Preset",
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
    collection_custom_suffix: bpy.props.StringProperty(
        name="Custom Suffix",
        description="Custom suffix for collection names",
        default=""
    )
    collection_custom_prefix: bpy.props.StringProperty(
        name="Custom Prefix",
        description="Custom prefix for collection names",
        default=""
    )
    overwrite_collection_name: bpy.props.StringProperty(
        name="Name",
        description="Overwrite the name for the collection",
        default=""
    )
    overwrite_naming: bpy.props.BoolProperty(
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

from ..preferences.preferenecs import PROPERTY_METADATA
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

# --- Draw Helpers ---
def draw_operator_filepath_settings(layout, op):
    layout.label(text="Export Path Mode")
    row = layout.row()
    row.prop(op, "export_folder_mode", expand=True)
    if op.export_folder_mode == 'ABSOLUTE':
        layout.prop(op, "absolute_export_path")
    if op.export_folder_mode == 'RELATIVE':
        layout.prop(op, "relative_export_path")
    if op.export_folder_mode == 'MIRROR':
        layout.prop(op, "mirror_search_path", text="Search Path")
        layout.prop(op, "mirror_replacement_path", text="Replacement Path")
        try:
            from ..preferences.preferenecs import compute_mirror_preview
            preview_path = compute_mirror_preview(op)
            layout.label(text="Export Folder Preview:")
            row = layout.row(align=True)
            row.label(text=preview_path)
            import os
            if os.path.exists(preview_path):
                op_btn = row.operator("file.external_operation", text='', icon='FILE_FOLDER')
                op_btn.operation = 'FOLDER_OPEN'
                op_btn.filepath = preview_path
        except Exception:
            pass 