import bpy
from ..functions.collection_layer import set_active_layer_Collection
from ..core.export_formats import ExportFormats

# Module-level cache prevents GC of dynamic EnumProperty items (Blender gotcha)
_exporter_enum_items_cache = []


def _get_exporter_items(self, context):
    global _exporter_enum_items_cache
    collection = bpy.data.collections.get(self.collection_name)
    if not collection:
        _exporter_enum_items_cache = [('0', "No Collection", "", 0)]
        return _exporter_enum_items_cache

    items = []
    for i, exp in enumerate(collection.exporters):
        fmt_key = ExportFormats.get_key_from_op_type(str(type(exp.export_properties)))
        fmt = ExportFormats.get(fmt_key)
        fmt_label = fmt.label if fmt else "Unknown"
        filepath = exp.export_properties.filepath or ""
        if filepath:
            import os
            filename = os.path.basename(filepath) or filepath
            directory = os.path.dirname(filepath) or ""
            tooltip = directory if directory else filepath
        else:
            filename = "(no path)"
            tooltip = ""
        label = f"{fmt_label}  —  {filename}"
        items.append((str(i), label, tooltip, i))

    _exporter_enum_items_cache = items if items else [('0', "No Exporters", "", 0)]
    return _exporter_enum_items_cache


class SIMPLEEXPORT_OT_FixMultipleExporters(bpy.types.Operator):
    """Remove all but one exporter from a collection that has multiple exporters."""
    bl_idname = "simple_export.fix_multiple_exporters"
    bl_label = "Fix Multiple Exporters"
    bl_description = (
        "This collection has more than one exporter. "
        "Select which exporter to keep; all others will be removed."
    )
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty(
        name="Collection Name",
        default="",
        options={'HIDDEN'}
    )

    keep_exporter_index: bpy.props.EnumProperty(
        name="Exporter to Keep",
        description="Select which exporter to keep; all others will be removed",
        items=_get_exporter_items,
    )

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=500)

    def draw(self, context):
        layout = self.layout
        collection = bpy.data.collections.get(self.collection_name)
        if not collection:
            layout.label(text=f"Collection '{self.collection_name}' not found.", icon='ERROR')
            return
        count = len(collection.exporters)
        layout.label(text=f"Collection '{self.collection_name}' has {count} exporters.", icon='ERROR')
        layout.label(text="Select the exporter to keep:")
        layout.prop(self, "keep_exporter_index", text="")

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if not collection:
            self.report({'ERROR'}, f"Collection '{self.collection_name}' not found.")
            return {'CANCELLED'}
        if len(collection.exporters) <= 1:
            return {'CANCELLED'}

        try:
            keep_idx = int(self.keep_exporter_index)
        except (ValueError, TypeError):
            self.report({'ERROR'}, "Invalid exporter selection.")
            return {'CANCELLED'}

        total = len(collection.exporters)
        set_active_layer_Collection(collection.name)

        # Find a real window area — dialog popups lack one, causing exporter_remove poll to fail
        override = None
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                for region in area.regions:
                    if region.type == 'WINDOW':
                        override = {'window': window, 'area': area, 'region': region}
                        break
                if override:
                    break
            if override:
                break

        # Remove in descending order so lower indices remain stable
        indices_to_remove = sorted([i for i in range(total) if i != keep_idx], reverse=True)
        with context.temp_override(**(override or {})):
            for idx in indices_to_remove:
                bpy.ops.collection.exporter_remove(index=idx)

        self.report({'INFO'}, f"Kept exporter {keep_idx}; removed {len(indices_to_remove)} from '{self.collection_name}'.")
        return {'FINISHED'}


classes = (SIMPLEEXPORT_OT_FixMultipleExporters,)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
