import bpy
import os
from bpy.props import StringProperty, CollectionProperty, BoolProperty
from bpy_extras.io_utils import ImportHelper

from .. import __package__ as base_package


class SIMPLEEXPORT_OT_RelativeFolderPicker(bpy.types.Operator, ImportHelper):
    """Select a folder and store it as a relative or absolute path"""
    bl_idname = "simple_export.folder_path_relative_picker"
    bl_label = "Select Folder"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ""
    filter_glob: StringProperty(default="", options={'HIDDEN'})
    files: CollectionProperty(
        name="File list",
        type=bpy.types.OperatorFileListElement,
        options={'HIDDEN', 'SKIP_SAVE'},
    )
    context: StringProperty(default="SCENE", options={'HIDDEN'})
    use_relative_path: BoolProperty(
        name="Relative Path",
        description="Store the path relative to the .blend file. "
                    "Disable to store as an absolute path",
        default=True,
    )

    def invoke(self, context, event):
        props = context.scene if self.context == 'SCENE' else context.preferences.addons[base_package].preferences
        current_path = None
        if props.export_folder_mode == 'RELATIVE' and getattr(props, 'folder_path_relative', ''):
            current_path = bpy.path.abspath(props.folder_path_relative)
        elif props.export_folder_mode == 'ABSOLUTE' and getattr(props, 'folder_path_absolute', ''):
            current_path = props.folder_path_absolute
        if current_path:
            if os.path.isdir(current_path):
                self.filepath = current_path + os.sep
            elif os.path.isdir(os.path.dirname(current_path)):
                self.filepath = current_path
        return super().invoke(context, event)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_relative_path")

    def execute(self, context):
        directory = os.path.dirname(self.filepath)
        props = context.scene if self.context == 'SCENE' else context.preferences.addons[base_package].preferences

        if self.use_relative_path:
            if not bpy.data.filepath:
                self.report({'ERROR'}, "Save your .blend file first — relative paths are computed from the file's location on disk.")
                return {'CANCELLED'}

            blend_dir = os.path.dirname(bpy.data.filepath)
            try:
                rel_path = os.path.relpath(directory, blend_dir)
                rel_path = os.path.normpath(rel_path)
                props.folder_path_relative = "//" + rel_path
                props.export_folder_mode = 'RELATIVE'
                self.report({'INFO'}, f"Relative path: {props.folder_path_relative}")
            except ValueError as e:
                self.report({'ERROR'}, f"Could not compute relative path: {e}")
                return {'CANCELLED'}
        else:
            props.folder_path_absolute = directory
            props.export_folder_mode = 'ABSOLUTE'
            self.report({'INFO'}, f"Absolute path: {directory}")

        return {'FINISHED'}


class SIMPLEEXPORT_OT_CollectionFilepathPicker(bpy.types.Operator, ImportHelper):
    """Browse for an export file path for this collection"""
    bl_idname = "simple_export.collection_filepath_picker"
    bl_label = "Browse Export Path"
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ""
    filter_glob: StringProperty(default="", options={'HIDDEN'})

    collection_name: StringProperty(default="", options={'HIDDEN'})
    use_relative_path: BoolProperty(
        name="Relative Path",
        description="Store the path relative to the .blend file. "
                    "Disable to store as an absolute path",
        default=True,
    )

    def invoke(self, context, event):
        collection = bpy.data.collections.get(self.collection_name)
        if collection:
            from ..functions.exporter_funcs import find_exporter
            scene = context.scene
            format_filter = scene.filter_format if scene.filter_format != 'ALL' else None
            exporter = find_exporter(collection, format_filter=format_filter)
            if exporter and exporter.export_properties.filepath:
                raw_path = exporter.export_properties.filepath
                self.use_relative_path = raw_path.startswith("//")
                abs_path = os.path.normpath(bpy.path.abspath(raw_path))
                if os.path.isdir(os.path.dirname(abs_path)):
                    self.filepath = abs_path
        return super().invoke(context, event)

    def draw(self, context):
        self.layout.prop(self, "use_relative_path")

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if not collection:
            self.report({'ERROR'}, f"Collection '{self.collection_name}' not found")
            return {'CANCELLED'}

        if self.use_relative_path:
            if not bpy.data.filepath:
                self.report({'ERROR'}, "Save your .blend file first — relative paths are computed from the file's location on disk.")
                return {'CANCELLED'}
            blend_dir = os.path.dirname(bpy.data.filepath)
            try:
                rel_path = os.path.relpath(self.filepath, blend_dir)
                rel_path = os.path.normpath(rel_path).replace("\\", "/")
                new_path = "//" + rel_path
            except ValueError as e:
                self.report({'ERROR'}, f"Could not compute relative path: {e}")
                return {'CANCELLED'}
        else:
            new_path = self.filepath

        collection.simple_export_filepath_proxy = new_path
        self.report({'INFO'}, f"Export path: {new_path}")
        return {'FINISHED'}


classes = (
    SIMPLEEXPORT_OT_RelativeFolderPicker,
    SIMPLEEXPORT_OT_CollectionFilepathPicker,
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
