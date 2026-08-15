import bpy

from .. import __package__ as base_package

_ENGINE_LABELS = {
    'UNITY': "Unity",
    'GODOT': "Godot",
    'UNREAL': "Unreal",
}


def _enabled_engines(prefs):
    """Engines that both have an adapter and are enabled in preferences."""
    from ..engine_bridge import available_engine_ids
    enabled = []
    for engine_id in available_engine_ids():
        settings = getattr(prefs, f"engine_mcp_{engine_id.lower()}", None)
        if settings is None or not settings.enabled:
            continue
        if engine_id == 'UNREAL' and not prefs.engine_mcp_unreal_experimental_ack:
            continue
        enabled.append(engine_id)
    return enabled


class SIMPLEEXPORT_MT_verify_in_engine_menu(bpy.types.Menu):
    """Pick which enabled engine to verify a collection's export in.

    Reads the target collection/filepath from WindowManager string props set
    by the caller (e.g. ui/result_popups.py) immediately before invoking this
    menu, since bpy.types.Menu.draw() cannot receive custom arguments."""
    bl_idname = "SIMPLEEXPORT_MT_verify_in_engine_menu"
    bl_label = "Verify in Engine"

    def draw(self, context):
        layout = self.layout
        prefs = context.preferences.addons[base_package].preferences
        wm = context.window_manager
        collection_name = wm.simple_export_engine_verify_pending_collection
        filepath = wm.simple_export_engine_verify_pending_filepath

        for engine_id in _enabled_engines(prefs):
            op = layout.operator("simple_export.verify_in_engine", text=_ENGINE_LABELS.get(engine_id, engine_id))
            op.engine_id = engine_id
            op.collection_name = collection_name
            op.filepath = filepath


class SIMPLEEXPORT_PT_EngineVerifyResultsPanel(bpy.types.Panel):
    """Panel showing the result of the last engine-verification run: pass/fail,
    a screenshot from the engine, and any issues found - reusing the same
    UIList and WindowManager collection the pre-export validator uses."""
    bl_idname = "SIMPLEEXPORT_PT_EngineVerifyResultsPanel"
    bl_label = "Engine Verification Results"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_ui_units_x = 40

    def draw(self, context):
        layout = self.layout
        wm = context.window_manager

        results = wm.simple_export_validation_results
        error_count = sum(1 for r in results if r.check_id.startswith('engine_') and r.severity == 'ERROR')
        warning_count = sum(1 for r in results if r.check_id.startswith('engine_') and r.severity == 'WARNING')

        row = layout.row(align=True)
        if error_count:
            row.label(text=f"{error_count} error(s) found", icon='CANCEL')
        elif warning_count:
            row.label(text=f"Passed with {warning_count} warning(s)", icon='ERROR')
        else:
            row.label(text="Verification passed", icon='CHECKMARK')

        image_name = wm.simple_export_engine_verify_image_name
        image = bpy.data.images.get(image_name) if image_name else None
        if image is not None:
            image.preview_ensure()
            if image.preview:
                layout.template_icon(icon_value=image.preview.icon_id, scale=10.0)

        layout.template_list(
            'SIMPLEEXPORT_UL_validation_results', '',
            wm, 'simple_export_validation_results',
            wm, 'simple_export_validation_index',
            rows=6,
        )

        layout.operator('simple_export.copy_validation_report', icon='COPYDOWN')


classes = (
    SIMPLEEXPORT_MT_verify_in_engine_menu,
    SIMPLEEXPORT_PT_EngineVerifyResultsPanel,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    wm = bpy.types.WindowManager
    wm.simple_export_engine_verify_running = bpy.props.BoolProperty(default=False, options={'SKIP_SAVE'})
    wm.simple_export_engine_verify_image_name = bpy.props.StringProperty(default="", options={'SKIP_SAVE'})
    wm.simple_export_engine_verify_pending_collection = bpy.props.StringProperty(default="", options={'SKIP_SAVE'})
    wm.simple_export_engine_verify_pending_filepath = bpy.props.StringProperty(default="", options={'SKIP_SAVE'})


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)

    wm = bpy.types.WindowManager
    for attr in (
        'simple_export_engine_verify_running',
        'simple_export_engine_verify_image_name',
        'simple_export_engine_verify_pending_collection',
        'simple_export_engine_verify_pending_filepath',
    ):
        if hasattr(wm, attr):
            delattr(wm, attr)
