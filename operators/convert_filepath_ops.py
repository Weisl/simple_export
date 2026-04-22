import bpy

from ..functions.exporter_funcs import find_exporter


class SIMPLEEXPORT_OT_ConvertFilepath(bpy.types.Operator):
    """Convert export filepaths between absolute and relative (// prefix) forms."""
    bl_idname = "simple_export.convert_filepath"
    bl_label = "Convert Filepath"
    bl_options = {'REGISTER', 'UNDO'}

    individual_collection: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    collection_name: bpy.props.StringProperty(default='', options={'HIDDEN'})
    to_relative: bpy.props.BoolProperty(
        name="To Relative",
        description="Convert to relative path (True) or to absolute path (False)",
        default=True,
        options={'HIDDEN'},
    )

    def execute(self, context):
        if not bpy.data.filepath and self.to_relative:
            self.report({'WARNING'}, "Save the .blend file before converting to relative paths.")
            return {'CANCELLED'}

        collections = self._get_collections(context)
        if not collections:
            self.report({'WARNING'}, "No valid collections found.")
            return {'CANCELLED'}

        converted = 0
        skipped = 0
        for collection in collections:
            scene = context.scene
            format_filter = scene.filter_format if scene.filter_format != 'ALL' else None
            exporter = find_exporter(collection, format_filter=format_filter)
            if not exporter:
                skipped += 1
                continue

            filepath = exporter.export_properties.filepath
            if not filepath:
                skipped += 1
                continue

            if self.to_relative:
                if filepath.startswith("//"):
                    skipped += 1
                    continue
                new_path = bpy.path.relpath(filepath)
            else:
                if not filepath.startswith("//"):
                    skipped += 1
                    continue
                new_path = bpy.path.abspath(filepath)

            exporter.export_properties.filepath = new_path
            converted += 1

        direction = "relative" if self.to_relative else "absolute"
        if converted:
            self.report({'INFO'}, f"Converted {converted} filepath(s) to {direction}.")
        else:
            self.report({'INFO'}, f"No filepaths needed conversion to {direction}.")

        return {'FINISHED'}

    def _get_collections(self, context):
        if self.individual_collection and self.collection_name:
            col = bpy.data.collections.get(self.collection_name)
            return [col] if col else []
        return [
            col for col in bpy.data.collections
            if getattr(col, "simple_export_selected", False) and col.exporters
        ]


classes = (
    SIMPLEEXPORT_OT_ConvertFilepath,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
