import bpy

from .presets_data import presets
from .. import __package__ as base_package


class EXPORT_OT_ApplyPreset(bpy.types.Operator):
    """
    Operator to set the preferences for the 'simple_collider' addon based on a selected preset.
    """
    bl_idname = "object.apply_export_preset"
    bl_label = "Apply Preset Settings"
    preset_name: bpy.props.StringProperty()

    def execute(self, context):
        # TODO: Should be applied to the exporter settings and not the preferences
        # 1. figure out the current collection and exporter
        # 2. get the preset data
        # 3. apply the preset values to the active collection exporter
        prefs = bpy.context.preferences.addons[base_package].preferences
        preset = presets[self.preset_name]

        for key, value in preset.items():
            setattr(prefs, key, value)

        return {'FINISHED'}


classes = (EXPORT_OT_ApplyPreset,)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
