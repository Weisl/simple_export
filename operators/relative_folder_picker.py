import bpy
import os
from bpy.props import StringProperty, CollectionProperty
from bpy_extras.io_utils import ImportHelper

from .. import __package__ as base_package


class SIMPLEEXPORT_OT_RelativeFolderPicker(bpy.types.Operator, ImportHelper):
    """Select a folder and print its relative path (must be inside the blend file's directory)"""
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
    context: bpy.props.StringProperty(default="SCENE", options={'HIDDEN'})

    def execute(self, context):
        if not bpy.data.filepath:
            self.report({'ERROR'}, "Save your blend file first!")
            return {'CANCELLED'}

        directory = os.path.dirname(self.filepath)
        blend_dir = os.path.dirname(bpy.data.filepath)

        try:
            rel_path = os.path.relpath(directory, blend_dir)
            # Normalize the path
            rel_path = os.path.normpath(rel_path)

            props = context.scene if self.context == 'SCENE' else context.preferences.addons[base_package].preferences
            # Store the relative path in the scene property
            props.folder_path_relative = "//" + rel_path

            print("Selected folder (relative path):", context.scene.folder_path_relative)
            self.report({'INFO'}, f"Relative path: {context.scene.folder_path_relative}")
        except ValueError as e:
            self.report({'ERROR'}, f"Could not compute relative path: {e}")
            return {'CANCELLED'}

        return {'FINISHED'}


classes = (
    SIMPLEEXPORT_OT_RelativeFolderPicker,
)


# Register the scene property
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
