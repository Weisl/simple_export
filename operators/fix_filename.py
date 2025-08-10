import bpy
import os

from ..core.export_path_func import generate_base_name
from ..functions.exporter_funcs import find_exporter
from ..operators.shared_properties import SharedPathProps, SharedFilenameProps


class SIMPLEEXPORT_OT_FixExportFilename(SharedPathProps, SharedFilenameProps, bpy.types.Operator):
    """Fix the export filename for a collection."""
    bl_idname = "simple_export.fix_export_filename"
    bl_label = "Fix Export Filename"
    bl_description = "Fix the export filename for a collection by applying the current naming conventions."
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    # Internal Properties
    collection_name: bpy.props.StringProperty(
        name="Collection Name",
        description="Name of the collection to fix",
        default="",
        options={'HIDDEN'}
    )

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if not collection or not collection.exporters:
            return {'CANCELLED'}

        scene = context.scene
        exporter = find_exporter(collection, format_filter= scene.export_format)
        if not exporter:
            return {'CANCELLED'}

        export_path = exporter.export_properties.filepath
        export_dir = os.path.dirname(export_path)
        _, ext = os.path.splitext(export_path)

        base_name = generate_base_name(collection.name, self.filename_prefix,
                                       self.filename_suffix,
                                       self.filename_blend_prefix)

        new_export_path = os.path.join(export_dir, f"{base_name}{ext}")
        exporter.export_properties.filepath = new_export_path
        collection["prev_name"] = collection.name

        return {'FINISHED'}
