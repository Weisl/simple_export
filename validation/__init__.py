import bpy

from . import operators
from . import properties

classes = (
    properties.ValidationIssueItem,
    operators.SIMPLEEXPORT_UL_validation_results,
    operators.SIMPLEEXPORT_OT_select_validation_target,
    operators.SIMPLEEXPORT_OT_copy_validation_report,
    operators.SCENE_OT_ValidateExportCollections,
)


def _clear_results_on_load(dummy=None):
    """Results live on WindowManager, which isn't saved with the .blend file
    and isn't cleared automatically on load - without this, switching files
    leaves a stale report from the previous file on screen until the user
    manually re-runs Validate Selected."""
    wm = bpy.context.window_manager
    if wm is not None:
        wm.simple_export_validation_results.clear()
        wm.simple_export_validation_index = 0


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    wm = bpy.types.WindowManager
    wm.simple_export_validation_results = bpy.props.CollectionProperty(type=properties.ValidationIssueItem)
    wm.simple_export_validation_index = bpy.props.IntProperty()

    bpy.app.handlers.load_post.append(_clear_results_on_load)


def unregister():
    from bpy.utils import unregister_class

    if _clear_results_on_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(_clear_results_on_load)

    wm = bpy.types.WindowManager
    if hasattr(wm, 'simple_export_validation_index'):
        del wm.simple_export_validation_index
    if hasattr(wm, 'simple_export_validation_results'):
        del wm.simple_export_validation_results

    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
