import bpy

from ..functions.copy_settings import copy_collection_export_settings
from ..functions.exporter_funcs import find_exporter
from ..functions.outliner_func import get_outliner_collections

# Collection names may contain commas, so the target list is newline separated
_NAME_SEPARATOR = '\n'


class SIMPLEEXPORT_OT_copy_export_settings(bpy.types.Operator):
    """Copy the export settings of a collection to the other collections selected in the Outliner"""
    bl_idname = "simple_export.copy_export_settings"
    bl_label = "Copy Export Settings"
    bl_description = ("Copy the export settings of this collection to the other collections selected in the "
                      "Outliner. Ctrl+click the target collections first, then right-click the collection to "
                      "copy from. File paths are never copied.")
    bl_options = {'REGISTER', 'UNDO'}

    source_name: bpy.props.StringProperty(
        name="Source Collection",
        description="Name of the collection to copy the settings from",
        default='',
        options={'HIDDEN'}
    )
    # Stores the target collection names captured at invoke time,
    # because context.selected_ids is unavailable after the dialog opens.
    target_names: bpy.props.StringProperty(default='', options={'HIDDEN'})

    copy_exporter_settings: bpy.props.BoolProperty(
        name="Exporter Settings",
        description="Copy the settings of the export format. The target is switched to the source's format "
                    "if it uses a different one, keeping its folder and file name",
        default=True
    )
    copy_pre_export_ops: bpy.props.BoolProperty(
        name="Pre-Export Operations",
        description="Copy Move to Origin, Triangulate, Apply Transform and Pre-Rotate settings",
        default=True
    )
    copy_group: bpy.props.BoolProperty(
        name="User Group",
        description="Copy the user group used for filtering the export list",
        default=True
    )

    def _target_collections(self, source=None):
        names = [n for n in self.target_names.split(_NAME_SEPARATOR) if n]
        collections = [bpy.data.collections.get(n) for n in names]
        return [c for c in collections if c and c != source]

    def invoke(self, context, event):
        source = bpy.data.collections.get(self.source_name)
        if not source:
            self.report({'ERROR'}, f"Collection '{self.source_name}' not found.")
            return {'CANCELLED'}

        targets = [c for c in get_outliner_collections(context) if c != source]
        if not targets:
            self.report({'WARNING'}, "Select the collections to copy to in the Outliner as well.")
            return {'CANCELLED'}

        self.target_names = _NAME_SEPARATOR.join(c.name for c in targets)
        return context.window_manager.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        count = len(self._target_collections())
        layout.label(text=f"Copy from '{self.source_name}' to {count} collection{'s' if count != 1 else ''}",
                     icon='INFO')

        col = layout.column(align=True)
        col.prop(self, 'copy_exporter_settings')
        col.prop(self, 'copy_pre_export_ops')
        col.prop(self, 'copy_group')

        layout.label(text="File paths are not copied.")

    def execute(self, context):
        source = bpy.data.collections.get(self.source_name)
        if not source:
            self.report({'ERROR'}, f"Collection '{self.source_name}' not found.")
            return {'CANCELLED'}

        if not (self.copy_exporter_settings or self.copy_pre_export_ops or self.copy_group):
            self.report({'WARNING'}, "Nothing to copy: enable at least one option.")
            return {'CANCELLED'}

        if self.copy_exporter_settings and not find_exporter(source):
            self.report({'ERROR'}, f"'{source.name}' has no exporter to copy from.")
            return {'CANCELLED'}

        targets = self._target_collections(source)
        if not targets:
            self.report({'WARNING'}, "No target collections found.")
            return {'CANCELLED'}

        # The exporter helpers make each target the active collection; put it back afterwards
        view_layer = context.view_layer
        previous_active = view_layer.active_layer_collection

        results = []
        try:
            for target in targets:
                if target.library is not None:
                    results.append({'name': target.name, 'success': False,
                                    'message': "Linked collections are read-only."})
                    continue
                try:
                    results.append(copy_collection_export_settings(
                        self, context, source, target,
                        exporter=self.copy_exporter_settings,
                        pre_export=self.copy_pre_export_ops,
                        group=self.copy_group))
                except Exception as e:
                    results.append({'name': target.name, 'success': False, 'message': str(e)})
        finally:
            view_layer.active_layer_collection = previous_active

        failed = [r for r in results if not r['success']]
        copied = len(results) - len(failed)
        if not copied:
            for r in failed:
                self.report({'WARNING'}, f"{r['name']}: {r['message']}")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Copied export settings from '{source.name}' to {copied} "
                              f"collection{'s' if copied != 1 else ''}.")
        for r in failed:
            self.report({'WARNING'}, f"{r['name']}: {r['message']}")
        return {'FINISHED'}


classes = (
    SIMPLEEXPORT_OT_copy_export_settings,
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
