import bpy

from ..core.info import COLOR_TAG_ICONS

# Reuses the icon convention already established in ui/result_popups.py:
# CANCEL = hard failure, ERROR = warning (yellow triangle), INFO = informational.
_SEVERITY_ICON = {'ERROR': 'CANCEL', 'WARNING': 'ERROR', 'INFO': 'INFO'}


class SIMPLEEXPORT_UL_validation_results(bpy.types.UIList):
    """List of export-collection validation issues, grouped by the collection
    they concern (a bold header naming the collection precedes its issues,
    since the flat results collection is already grouped in that order -
    collect_validation_issues() appends every issue for one collection before
    moving to the next). Each row has a dedicated arrow button to select/frame
    the offending object (or every object in the collection, for a
    collection-level issue); the message itself is a plain, non-interactive
    label. Supports filtering by severity (three-tier: Error/Warning/Info) and
    a free-text search across the collection/object name/message.

    The severity toggles themselves live on WindowManager, not here - they're
    drawn above the list (with per-severity counts) by the operator's draw(),
    not tucked away behind the UIList's own collapsible filter icon. This
    class only reads them (`data.simple_export_validation_show_*`, where
    `data` is the WindowManager passed into template_list/filter_items).
    """

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        results = data.simple_export_validation_results
        # Grouping must walk back to the previous *visible* item, not just
        # index - 1: when filtering hides some rows, the item right before
        # this one in the raw collection may belong to the same collection but
        # not be shown, which would otherwise wrongly suppress this row's
        # header (see filter_items, which caches the same flags used here).
        visible_flags = getattr(self, '_visible_flags', None)
        is_group_start = True
        if visible_flags is not None:
            for i in range(index - 1, -1, -1):
                if visible_flags[i]:
                    is_group_start = results[i].collection_name != item.collection_name
                    break
        elif index > 0:
            is_group_start = results[index - 1].collection_name != item.collection_name

        col = layout.column(align=True)
        if is_group_start:
            collection = bpy.data.collections.get(item.collection_name)
            color_tag = collection.color_tag if collection else 'NONE'
            col.label(text=item.collection_name, icon=COLOR_TAG_ICONS.get(color_tag, 'OUTLINER_COLLECTION'))

        row = col.row(align=True)
        row.alert = item.severity == 'ERROR'
        select_op = row.operator('simple_export.select_validation_target', text='', icon='FORWARD')
        select_op.collection_name = item.collection_name
        select_op.object_name = item.object_name

        text = f"{item.object_name}: {item.message}" if item.object_name else item.message
        row.label(text=text, icon=_SEVERITY_ICON.get(item.severity, 'INFO'))

    def filter_items(self, context, data, propname):
        results = getattr(data, propname)
        flt_flags = [self.bitflag_filter_item] * len(results)

        filter_text = self.filter_name.lower()
        for idx, item in enumerate(results):
            if item.severity == 'ERROR' and not data.simple_export_validation_show_errors:
                flt_flags[idx] = 0
            elif item.severity == 'WARNING' and not data.simple_export_validation_show_warnings:
                flt_flags[idx] = 0
            elif item.severity == 'INFO' and not data.simple_export_validation_show_info:
                flt_flags[idx] = 0
            elif filter_text and (
                filter_text not in item.collection_name.lower()
                and filter_text not in item.object_name.lower()
                and filter_text not in item.message.lower()
            ):
                flt_flags[idx] = 0

        # Cached for draw_item's grouping logic above - filter_items always
        # runs before draw_item within the same template_list draw call.
        self._visible_flags = flt_flags
        return flt_flags, []

    def draw_filter(self, context, layout):
        row = layout.row(align=True)
        row.prop(self, 'filter_name', text='', icon='VIEWZOOM')


def _frame_selected(context):
    """Best-effort viewport framing after a selection change from within the
    validation popup. Selection itself is the important part of the action -
    framing is skipped rather than raised as an error if no 3D viewport can be
    found (e.g. a very unusual screen layout)."""
    if context.area and context.area.type == 'VIEW_3D' and context.region:
        with context.temp_override(area=context.area, region=context.region):
            bpy.ops.view3d.view_selected()
        return

    for window in context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != 'VIEW_3D':
                continue
            region = next((r for r in area.regions if r.type == 'WINDOW'), None)
            if region is None:
                continue
            with context.temp_override(window=window, area=area, region=region):
                bpy.ops.view3d.view_selected()
            return


class SIMPLEEXPORT_OT_select_validation_target(bpy.types.Operator):
    """Select and frame the object (or every object in the collection, for a
    collection-level issue) referenced by this validation result"""
    bl_idname = "simple_export.select_validation_target"
    bl_label = "Select Object"
    bl_options = {'REGISTER', 'INTERNAL'}

    collection_name: bpy.props.StringProperty()
    object_name: bpy.props.StringProperty()

    def execute(self, context):
        for selected in context.selected_objects:
            selected.select_set(False)

        if self.object_name:
            obj = bpy.data.objects.get(self.object_name)
            if obj is None:
                self.report({'WARNING'}, f"Object '{self.object_name}' no longer exists")
                return {'CANCELLED'}
            obj.select_set(True)
            context.view_layer.objects.active = obj
        else:
            collection = bpy.data.collections.get(self.collection_name)
            if collection is None:
                self.report({'WARNING'}, f"Collection '{self.collection_name}' no longer exists")
                return {'CANCELLED'}
            objs = list(collection.objects)
            if not objs:
                self.report({'WARNING'}, f"Collection '{self.collection_name}' has no objects")
                return {'CANCELLED'}
            for obj in objs:
                obj.select_set(True)
            context.view_layer.objects.active = objs[0]

        _frame_selected(context)
        return {'FINISHED'}


class SIMPLEEXPORT_OT_copy_validation_report(bpy.types.Operator):
    """Copy the validation report to the clipboard"""
    bl_idname = "simple_export.copy_validation_report"
    bl_label = "Copy Report to Clipboard"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        wm = context.window_manager
        results = wm.simple_export_validation_results
        if not results:
            self.report({'INFO'}, "No validation issues to copy")
            return {'CANCELLED'}

        lines = []
        current_collection = None
        for item in results:
            if item.collection_name != current_collection:
                if current_collection is not None:
                    lines.append('')
                lines.append(item.collection_name)
                current_collection = item.collection_name
            target = f" ({item.object_name})" if item.object_name else ""
            lines.append(f"  [{item.severity}] {item.message}{target}")

        wm.clipboard = '\n'.join(lines)
        self.report({'INFO'}, "Validation report copied to clipboard")
        return {'FINISHED'}


class SCENE_OT_ValidateExportCollections(bpy.types.Operator):
    """Check export collections for common problems - missing materials, UVs, tris budget, n-gons, non-manifold geometry, etc."""
    bl_idname = "simple_export.validate_collections"
    bl_label = "Validate Selected"
    bl_options = {'REGISTER'}

    scope: bpy.props.EnumProperty(
        name="Scope",
        items=(
            ('SELECTED', "Selected Export Collections", "Check only collections checked for export"),
            ('ALL', "All Export Collections", "Check every collection that has an exporter assigned"),
        ),
        default='SELECTED',
        # No update= callback here: Blender can invoke an EnumProperty's update
        # callback with `self` bound to a bare properties proxy rather than the
        # full operator instance (e.g. whenever a caller pre-sets `op.scope`
        # before the operator is invoked, which every "Validate Selected"
        # button in this addon does) - that proxy doesn't carry `_rescan`.
        # draw() always runs against the real instance, so the rescan-on-
        # scope-change behavior is implemented there instead (see draw()).
    )

    # Internal properties - parity with SCENE_OT_ExportCollectionsSelection so this
    # operator can later be invoked from a context menu or per-row button.
    outliner: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    individual_collection: bpy.props.BoolProperty(default=False, options={'HIDDEN'})
    collection_name: bpy.props.StringProperty(default='', options={'HIDDEN'})

    def _collections(self, context):
        if self.scope == 'ALL':
            return [col for col in bpy.data.collections if col.exporters]
        from ..functions.collection_selection import get_export_collection_list
        return get_export_collection_list(
            context, outliner=self.outliner,
            individual_collection=self.individual_collection,
            collection_name=self.collection_name,
        )

    def _rescan(self, context):
        from .. import __package__ as base_package
        from .checks import collect_validation_issues

        prefs = context.preferences.addons[base_package].preferences
        depsgraph = context.evaluated_depsgraph_get()
        wm = context.window_manager

        wm.progress_begin(0, 1)
        try:
            issues = collect_validation_issues(
                self._collections(context), prefs, depsgraph,
                progress_callback=lambda done, total: wm.progress_update(done / total if total else 1),
            )
        finally:
            wm.progress_end()

        results = wm.simple_export_validation_results
        results.clear()
        for issue in issues:
            item = results.add()
            item.check_id = issue.check_id
            item.collection_name = issue.collection_name
            item.object_name = issue.object_name
            item.severity = issue.severity
            item.message = issue.message
        wm.simple_export_validation_index = 0

    def invoke(self, context, event):
        self._last_scope = self.scope
        self._rescan(context)

        if len(context.window_manager.simple_export_validation_results) == 0:
            self.report({'INFO'}, "No issues found")
            return {'FINISHED'}

        return context.window_manager.invoke_props_dialog(self, width=480)

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager

        if self.scope != getattr(self, '_last_scope', self.scope):
            self._last_scope = self.scope
            self._rescan(context)

        row = layout.row()
        row.prop(self, 'scope', expand=True)

        results = wm.simple_export_validation_results
        error_count = sum(1 for r in results if r.severity == 'ERROR')
        warning_count = sum(1 for r in results if r.severity == 'WARNING')
        info_count = sum(1 for r in results if r.severity == 'INFO')

        # Severity filter, always visible above the list (not tucked away
        # behind the UIList's own collapsible filter icon).
        row = layout.row(align=True)
        row.prop(wm, 'simple_export_validation_show_errors', toggle=True,
                 icon=_SEVERITY_ICON['ERROR'], text=f"Errors ({error_count})")
        row.prop(wm, 'simple_export_validation_show_warnings', toggle=True,
                 icon=_SEVERITY_ICON['WARNING'], text=f"Warnings ({warning_count})")
        row.prop(wm, 'simple_export_validation_show_info', toggle=True,
                 icon=_SEVERITY_ICON['INFO'], text=f"Info ({info_count})")

        layout.template_list(
            'SIMPLEEXPORT_UL_validation_results', '',
            wm, 'simple_export_validation_results',
            wm, 'simple_export_validation_index',
            rows=8,
        )

        layout.operator('simple_export.copy_validation_report', icon='COPYDOWN')

    def execute(self, context):
        return {'FINISHED'}


classes = (
    SIMPLEEXPORT_UL_validation_results,
    SIMPLEEXPORT_OT_select_validation_target,
    SIMPLEEXPORT_OT_copy_validation_report,
    SCENE_OT_ValidateExportCollections,
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
