import bpy
import os
import textwrap

from .. import __package__ as base_package
from ..core.info import COLOR_TAG_ICONS, SEVERITY_ICONS

# Per-box, per-severity "is this section expanded" state for the export
# results popup. Keyed by collection name (unique within one export batch).
# Not a bpy.props.BoolProperty because export_data_info has no PropertyGroup
# backing it - see _sync_expand_state_with_results().
# Shape: {collection_name: {'ERROR': bool, 'WARNING': bool, 'INFO': bool, 'STATS': bool}}
_result_expand_state = {}
_last_export_data_info = None
_DEFAULT_EXPAND = {'ERROR': True, 'WARNING': False, 'INFO': False, 'STATS': True}


def _sync_expand_state_with_results(results_str):
    """Reset per-box expand state whenever a fresh export overwrote the
    results, so boxes don't inherit stale toggles from a previous run."""
    global _last_export_data_info
    if results_str != _last_export_data_info:
        _result_expand_state.clear()
        _last_export_data_info = results_str


def _get_box_state(collection_name):
    return _result_expand_state.setdefault(collection_name, dict(_DEFAULT_EXPAND))


def _build_clipboard_text(message, warnings):
    parts = [message] + [f"! [{w['severity']}] {w['message']}" for w in warnings]
    return "\n".join(filter(None, parts))


def _draw_messages(col, message, warnings, width=55):
    for line in textwrap.wrap(message, width=width) or [message]:
        col.label(text=line)
    for w in warnings:
        lines = textwrap.wrap(w, width=width - 2) or [w]
        for i, line in enumerate(lines):
            # Icon only on the first wrapped line of each warning, not repeated per line.
            col.label(text=line, icon='ERROR' if i == 0 else 'NONE')


def _draw_stats_sublist(col, collection_name, state, key, label, icon, names):
    """One row: 'Label (N)' that expands into an indented list of names.
    Mirrors the ERROR/WARNING/INFO severity toggle pattern, keyed under its
    own state key so it can be expanded independently of the parent
    Statistics section."""
    row = col.row(align=True)
    if names:
        toggle = row.operator(
            SIMPLEEXPORTER_OT_ToggleResultSeverity.bl_idname,
            text=f"{label} ({len(names)})", icon=icon,
            depress=state.get(key, False),
        )
        toggle.collection_name = collection_name
        toggle.severity = key
    else:
        row.label(text=f"{label}: 0", icon=icon)

    if names and state.get(key, False):
        indented = col.row()
        indented.separator(factor=2.0)
        sub_col = indented.column(align=True)
        for n in names:
            sub_col.label(text=n)


def _draw_verify_in_engine_button(context, layout, result):
    """Adds a "Verify in Engine" button/menu for a successful export result,
    if at least one engine is enabled in preferences."""
    from ..engine_bridge import available_engine_ids, guess_engine_for_collection
    prefs = context.preferences.addons[base_package].preferences

    enabled_engines = []
    for engine_id in available_engine_ids():
        settings = getattr(prefs, f"engine_mcp_{engine_id.lower()}", None)
        if settings is None or not settings.enabled:
            continue
        if engine_id == 'UNREAL' and not prefs.engine_mcp_unreal_experimental_ack:
            continue
        enabled_engines.append(engine_id)

    if not enabled_engines:
        return

    collection = bpy.data.collections.get(result['name'])
    guessed = guess_engine_for_collection(collection)

    if guessed and guessed in enabled_engines:
        op = layout.operator("simple_export.verify_in_engine", text='', icon='RENDER_STILL')
        op.collection_name = result['name']
        op.engine_id = guessed
        op.filepath = result.get('filepath', '')
    else:
        context.window_manager.simple_export_engine_verify_pending_collection = result['name']
        context.window_manager.simple_export_engine_verify_pending_filepath = result.get('filepath', '')
        layout.menu("SIMPLEEXPORT_MT_verify_in_engine_menu", text='', icon='RENDER_STILL')


class SIMPLEEXPORTER_OT_ShowCollectionError(bpy.types.Operator):
    """Show the last export error for a specific collection."""
    bl_idname = "simple_export.show_collection_error"
    bl_label = "Export Error"
    bl_description = "Show the last export error for this collection"

    collection_name: bpy.props.StringProperty()
    message: bpy.props.StringProperty()
    warnings: bpy.props.StringProperty()

    def invoke(self, context, event):
        results_str = context.window_manager.export_data_info
        results = eval(results_str) if results_str else []
        for r in results:
            if r['name'] == self.collection_name and not r['success']:
                self.message = r.get('message', '')
                self.warnings = "\n".join(
                    f"! [{w['severity']}] {w['message']}" for w in r.get('warnings', [])
                )
                break
        else:
            self.message = "No error record found for this collection."
            self.warnings = ""
        return context.window_manager.invoke_popup(self, width=400)

    def draw(self, context):
        layout = self.layout
        layout.label(text=self.collection_name, icon='CANCEL')
        layout.separator()
        warnings = self.warnings.splitlines()
        _draw_messages(layout.column(align=True), self.message, warnings)
        layout.separator()
        op = layout.operator("simple_export.copy_to_clipboard", text="Copy Error", icon='COPYDOWN')
        # self.warnings already has "! [SEVERITY] ..." baked in from invoke() - plain join, no re-formatting.
        op.text = "\n".join(filter(None, [self.message, self.warnings]))

    def execute(self, context):
        return {'FINISHED'}


class SIMPLEEXPORTER_OT_CopyExportReport(bpy.types.Operator):
    """Copy a full export report (all collections, status, filepath, message) to the clipboard."""
    bl_idname = "simple_export.copy_export_report"
    bl_label = "Copy Full Report"
    bl_description = "Copy a full export report to the clipboard"

    def execute(self, context):
        results_str = context.window_manager.export_data_info
        results = eval(results_str) if results_str else []

        if not results:
            self.report({'WARNING'}, "No export results to report")
            return {'CANCELLED'}

        lines = ["Export Report", "=" * 60]
        success_count = sum(1 for r in results if r['success'])
        fail_count = len(results) - success_count

        for r in results:
            status = "OK  " if r['success'] else "FAIL"
            lines.append(f"[{status}]  {r['name']}")
            lines.append(f"       Path:    {r.get('filepath') or '-'}")
            detail = _build_clipboard_text(r.get('message', ''), r.get('warnings', []))
            if detail:
                lines.append(f"       Detail:  {detail}")

        lines.append("=" * 60)
        lines.append(f"Summary: {success_count} succeeded, {fail_count} failed")

        context.window_manager.clipboard = "\n".join(lines)
        self.report({'INFO'}, f"Report copied ({len(results)} entries)")
        return {'FINISHED'}


class SIMPLEEXPORTER_OT_CopyToClipboard(bpy.types.Operator):
    """Copy a message to the system clipboard."""
    bl_idname = "simple_export.copy_to_clipboard"
    bl_label = "Copy to Clipboard"
    bl_description = "Copy this message to the clipboard"

    text: bpy.props.StringProperty(name="Text", default="")

    def execute(self, context):
        context.window_manager.clipboard = self.text
        self.report({'INFO'}, "Copied to clipboard")
        return {'FINISHED'}


class SIMPLEEXPORTER_PT_PresetResultsPanel(bpy.types.Panel):
    """Panel to display the results of applying the preset."""
    bl_idname = "SIMPLEEXPORTER_PT_PresetResultsPanel"
    bl_label = "Preset Application Results"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 30

    def draw(self, context):
        layout = self.layout
        layout.label(text="Assign Export Format Presets:")

        # Get results from Scene
        results_str = context.window_manager.assign_preset_info_data
        results = eval(results_str) if results_str else []  # Parse results string into a list

        # Header row with column titles
        split = layout.split(factor=0.1)
        col_icon = split.column()  # Icon column
        col_name = split.column()  # Collection name column
        col_message = split.column()  # Info message column

        row = layout.row()
        col_icon.label(text="")
        col_name.label(text="Collection")
        col_message.label(text="Info")

        # Iterate over results and populate the table
        for result in results:
            split = layout.split(factor=0.05)  # Split for each row
            col_icon = split.column()
            col_name = split.column()
            col_message = split.column()

            # Icon Column
            col_icon.label(icon='CHECKMARK' if result['success'] else 'CANCEL')

            # Collection Name Column
            collection_name = result['name']
            collection = bpy.data.collections[collection_name]
            color_tag = collection.color_tag
            icon = COLOR_TAG_ICONS.get(color_tag, 'NONE')
            col_name.label(text=result['name'], icon=icon)

            # Info Message Column
            col_message.label(text=result['message'])


class SIMPLEEXPORTER_PT_AddExporterResultsPanel(bpy.types.Panel):
    """Panel to display the results of adding exporters to collections."""
    bl_idname = "SIMPLEEXPORTER_PT_AddExporterResultsPanel"
    bl_label = "Add Exporter Results"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 30

    def draw(self, context):
        layout = self.layout
        layout.label(text="Add Exporter to Collection:")

        # Get results from WindowManager
        results_str = context.window_manager.add_exporter_result_info
        results = eval(results_str) if results_str else []  # Parse results string into a list

        # Header row with column titles
        split = layout.split(factor=0.1)
        col_icon = split.column()  # Icon column
        col_name = split.column()  # Collection name column
        col_message = split.column()  # Info message column

        col_icon.label(text="")
        col_name.label(text="Collection")
        col_message.label(text="Info")

        # Iterate over results and populate the table
        for result in results:
            split = layout.split(factor=0.05)  # Split for each row
            col_icon = split.column()
            col_name = split.column()
            col_message = split.column()

            # Icon Column
            col_icon.label(icon='CHECKMARK' if result['success'] else 'CANCEL')

            # Collection Name Column
            collection_name = result['name']
            collection = bpy.data.collections.get(collection_name)
            color_tag = collection.color_tag if collection else 'NONE'
            icon = COLOR_TAG_ICONS.get(color_tag, 'NONE')
            col_name.label(text=result['name'], icon=icon)

            # Info Message Column
            col_message.label(text=result['message'])


class SIMPLEEXPORTER_PT_FilePathResultsPanel(bpy.types.Panel):
    """Panel to display the results of applying the filepath."""
    bl_idname = "SIMPLEEXPORTER_PT_FilePathResultsPanel"
    bl_label = "Preset Application Results"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 30

    def draw(self, context):
        layout = self.layout
        layout.label(text="Filepath Result Preset:")

        # Get results from WindowManager
        results_str = context.window_manager.assign_filepath_result_info
        results = eval(results_str) if results_str else []  # Parse results string into a list

        # Header row with column titles
        split = layout.split(factor=0.1)
        col_icon = split.column()  # Icon column
        col_name = split.column()  # Collection name column
        col_message = split.column()  # Info message column

        row = layout.row()
        col_icon.label(text="")
        col_name.label(text="Collection")
        col_message.label(text="Filepath")

        # Iterate over results and populate the table
        for result in results:
            split = layout.split(factor=0.05)  # Split for each row
            col_icon = split.column()
            col_name = split.column()
            col_message = split.column()

            # Icon Column
            col_icon.label(icon='CHECKMARK' if result['success'] else 'CANCEL')

            # Collection Name Column
            collection_name = result['name']
            collection = bpy.data.collections[collection_name]
            color_tag = collection.color_tag

            icon = COLOR_TAG_ICONS.get(color_tag, 'NONE')
            col_name.label(text=result['name'], icon=icon)

            # Info Message Column
            if result['success']:
                # Info Message Column
                col_message.label(text=result['filepath'])
            else:
                col_message.label(text=result['message'])


class SIMPLEEXPORTER_OT_ToggleResultSeverity(bpy.types.Operator):
    """Expand/collapse one severity's message list for one export result box."""
    bl_idname = "simple_export.toggle_result_severity"
    bl_label = "Toggle Severity Section"
    bl_options = {'REGISTER', 'INTERNAL'}

    collection_name: bpy.props.StringProperty()
    severity: bpy.props.StringProperty()

    def execute(self, context):
        state = _get_box_state(self.collection_name)
        state[self.severity] = not state.get(self.severity, False)
        return {'FINISHED'}


class SIMPLEEXPORTER_OT_SetAllResultSeverityExpand(bpy.types.Operator):
    """Force every non-empty severity section, in every result box, open or closed."""
    bl_idname = "simple_export.set_all_result_severity_expand"
    bl_label = "Expand/Collapse All Result Sections"
    bl_options = {'REGISTER', 'INTERNAL'}

    expand: bpy.props.BoolProperty()

    def execute(self, context):
        results_str = context.window_manager.export_data_info
        results = eval(results_str) if results_str else []
        for r in results:
            counts = {'ERROR': 0, 'WARNING': 0, 'INFO': 0}
            for w in r.get('warnings', []):
                counts[w.get('severity', 'INFO')] = counts.get(w.get('severity', 'INFO'), 0) + 1
            state = _get_box_state(r['name'])
            state['OPEN'] = self.expand
            for sev in ('ERROR', 'WARNING', 'INFO'):
                if counts.get(sev, 0) > 0:
                    state[sev] = self.expand
            stats = r.get('statistics')
            if stats:
                state['STATS'] = self.expand
                if stats.get('materials'):
                    state['STATS_MATERIALS'] = self.expand
                if stats.get('uv_sets'):
                    state['STATS_UVSETS'] = self.expand
        return {'FINISHED'}


# Popup to show export results
class SIMPLEEXPORTER_PT_ExportResultsPanel(bpy.types.Panel):
    """Panel to display the export results, one box per collection."""
    bl_idname = "SIMPLEEXPORTER_PT_ExportResultsPanel"
    bl_label = "Export Results"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 48

    def draw(self, context):
        layout = self.layout
        layout.label(text="Export Results:")

        results_str = context.window_manager.export_data_info
        _sync_expand_state_with_results(results_str)
        results = eval(results_str) if results_str else []

        if results:
            row = layout.row(align=True)
            op = row.operator(SIMPLEEXPORTER_OT_SetAllResultSeverityExpand.bl_idname, text="Expand All")
            op.expand = True
            op = row.operator(SIMPLEEXPORTER_OT_SetAllResultSeverityExpand.bl_idname, text="Collapse All")
            op.expand = False

        for result in results:
            name = result['name']
            success = result['success']
            warnings = result.get('warnings', [])
            message = result.get('message', '')
            filepath = result.get('filepath') or "-"
            state = _get_box_state(name)

            statistics = result.get('statistics')

            by_severity = {'ERROR': [], 'WARNING': [], 'INFO': []}
            for w in warnings:
                by_severity.setdefault(w.get('severity', 'INFO'), []).append(w)

            box = layout.box()

            # One-line collapsed header: chevron + status icon + name, buttons right-aligned.
            # Everything else (filepath, message, severity details) only draws when open.
            is_open = state.setdefault('OPEN', not success or bool(warnings) or bool(statistics))

            if not success:
                status_icon = 'CANCEL'
            elif warnings:
                status_icon = 'ERROR'  # succeeded, but flag that it has notes worth a look
            else:
                status_icon = 'CHECKMARK'

            header = box.row(align=True)
            header.label(text=name, icon=status_icon)

            # Filepath, always visible even while collapsed.
            header.label(text=filepath)

            # Severity counts + the expand/collapse toggle, grouped together and
            # always visible even while collapsed.
            counts_text = (
                f"Errors: {len(by_severity['ERROR'])}   "
                f"Warnings: {len(by_severity['WARNING'])}   "
                f"Infos: {len(by_severity['INFO'])}"
            )
            counts_row = header.row(align=True)
            counts_row.label(text=counts_text)
            chevron = counts_row.operator(
                SIMPLEEXPORTER_OT_ToggleResultSeverity.bl_idname,
                text="", icon='DISCLOSURE_TRI_DOWN' if is_open else 'DISCLOSURE_TRI_RIGHT',
            )
            chevron.collection_name = name
            chevron.severity = 'OPEN'

            btns = header.row(align=True)
            btns.alignment = 'RIGHT'
            if success and result.get('filepath'):
                export_dir = os.path.dirname(result['filepath'])
                btns.operator("wm.path_open", text='', icon='FILE_FOLDER').filepath = export_dir
                _draw_verify_in_engine_button(context, btns, result)
            if not success:
                copy_op = btns.operator("simple_export.copy_to_clipboard", text='', icon='COPYDOWN')
                copy_op.text = _build_clipboard_text(message, warnings)

            if not is_open:
                continue

            # Full-width filepath + message lines
            body = box.column(align=True)
            for line in textwrap.wrap(filepath, width=90) or [filepath]:
                body.label(text=line)
            for line in textwrap.wrap(message, width=90) or [message]:
                body.label(text=line)

            # Severity toggle row — only severities with items get a button
            sev_row = box.row(align=True)
            for sev in ('ERROR', 'WARNING', 'INFO'):
                items = by_severity[sev]
                if not items:
                    continue
                toggle = sev_row.operator(
                    SIMPLEEXPORTER_OT_ToggleResultSeverity.bl_idname,
                    text=f"{sev.title()} ({len(items)})",
                    icon=SEVERITY_ICONS[sev],
                    depress=state[sev],
                )
                toggle.collection_name = name
                toggle.severity = sev

            if statistics:
                stats_toggle = sev_row.operator(
                    SIMPLEEXPORTER_OT_ToggleResultSeverity.bl_idname,
                    text="Statistics", icon='MESH_DATA',
                    depress=state['STATS'],
                )
                stats_toggle.collection_name = name
                stats_toggle.severity = 'STATS'

            # Expanded per-severity message lists
            for sev in ('ERROR', 'WARNING', 'INFO'):
                items = by_severity[sev]
                if not items or not state[sev]:
                    continue
                indented = box.row()
                indented.separator(factor=2.0)
                col = indented.column(align=True)
                for w in items:
                    lines = textwrap.wrap(w['message'], width=85) or [w['message']]
                    for i, line in enumerate(lines):
                        col.label(text=line, icon=SEVERITY_ICONS[sev] if i == 0 else 'NONE')

            # Expanded statistics breakdown
            if statistics and state['STATS']:
                from ..core.info import OBJECT_TYPE_LABELS
                indented = box.row()
                indented.separator(factor=2.0)
                col = indented.column(align=True)
                object_parts = [
                    f"{OBJECT_TYPE_LABELS.get(obj_type, obj_type)}: {count}"
                    for obj_type, count in statistics['object_counts']
                ]
                col.label(text="Objects: " + (", ".join(object_parts) if object_parts else "-"), icon='OBJECT_DATA')
                _draw_stats_sublist(col, name, state, 'STATS_MATERIALS', "Materials", 'MATERIAL', statistics['materials'])
                _draw_stats_sublist(col, name, state, 'STATS_UVSETS', "UV Sets", 'UV', statistics['uv_sets'])

        layout.separator()
        layout.operator("simple_export.copy_export_report", text="Copy Full Report", icon='COPYDOWN')


classes = (
    SIMPLEEXPORTER_OT_ShowCollectionError,
    SIMPLEEXPORTER_OT_CopyExportReport,
    SIMPLEEXPORTER_OT_CopyToClipboard,
    SIMPLEEXPORTER_OT_ToggleResultSeverity,
    SIMPLEEXPORTER_OT_SetAllResultSeverityExpand,
    SIMPLEEXPORTER_PT_PresetResultsPanel,
    SIMPLEEXPORTER_PT_AddExporterResultsPanel,
    SIMPLEEXPORTER_PT_FilePathResultsPanel,
    SIMPLEEXPORTER_PT_ExportResultsPanel,
)


def register():
    bpy.types.WindowManager.export_data_info = bpy.props.StringProperty(default="[]")
    bpy.types.WindowManager.assign_filepath_result_info = bpy.props.StringProperty(default="[]")
    bpy.types.WindowManager.assign_preset_info_data = bpy.props.StringProperty(default="[]")
    bpy.types.WindowManager.add_exporter_result_info = bpy.props.StringProperty(default="[]")

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)

    del bpy.types.WindowManager.export_data_info
    del bpy.types.WindowManager.assign_filepath_result_info
    del bpy.types.WindowManager.assign_preset_info_data
    del bpy.types.WindowManager.add_exporter_result_info

    global _last_export_data_info
    _result_expand_state.clear()
    _last_export_data_info = None
