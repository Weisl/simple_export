import bpy
import os

from ..core.export_path_func import generate_base_name
from ..functions.exporter_funcs import find_exporter
from ..operators.shared_properties import SharedFilenameProps


class SIMPLEEXPORT_OT_FixExportFilename(SharedFilenameProps, bpy.types.Operator):
    """Fix the export filename for a collection."""
    bl_idname = "simple_export.fix_export_filename"
    bl_label = "Fix Export Filename"
    bl_description = "Fix the export filename for a collection by applying the current naming conventions."
    bl_options = {'REGISTER', 'UNDO'}

    # Internal Properties
    collection_name: bpy.props.StringProperty(
        name="Collection Name",
        description="Name of the collection to fix",
        default="",
        options={'HIDDEN'}
    )

    exporter_format: bpy.props.StringProperty(
        name="Exporter Format",
        description="Format key of the exporter to fix (e.g. 'FBX')",
        default="",
        options={'HIDDEN'}
    )

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if not collection or not collection.exporters:
            self.report({'WARNING'}, f"No exporters found for collection '{self.collection_name}'.")
            return {'CANCELLED'}

        scene = context.scene
        format_filter = self.exporter_format or scene.export_format or None
        exporter = find_exporter(collection, format_filter=format_filter)
        if not exporter:
            self.report({'WARNING'}, f"No matching exporter found for collection '{self.collection_name}'.")
            return {'CANCELLED'}

        export_path = exporter.export_properties.filepath

        last_sep = max(export_path.rfind('/'), export_path.rfind('\\'))
        dir_prefix = export_path[:last_sep + 1] if last_sep >= 0 else ""
        filename = export_path[last_sep + 1:] if last_sep >= 0 else export_path
        _, ext = os.path.splitext(filename)

        base_name = generate_base_name(collection.name, self.filename_prefix,
                                       self.filename_suffix,
                                       self.filename_blend_prefix,
                                       self.filename_separator)

        new_export_path = dir_prefix + base_name + ext
        exporter.export_properties.filepath = new_export_path
        collection["prev_name"] = collection.name

        return {'FINISHED'}

classes = (
    SIMPLEEXPORT_OT_FixExportFilename,
)


# Register the scene property
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
