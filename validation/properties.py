import bpy


class ValidationIssueItem(bpy.types.PropertyGroup):
    """One validation result, shown as a row in SIMPLEEXPORT_UL_validation_results."""
    check_id: bpy.props.StringProperty()
    collection_name: bpy.props.StringProperty()
    object_name: bpy.props.StringProperty()
    severity: bpy.props.StringProperty()
    message: bpy.props.StringProperty()
