import bpy

from .. import __package__ as base_package

def add_keymap():
    km = bpy.context.window_manager.keyconfigs.addon.keymaps.new(name="Window")
    prefs = bpy.context.preferences.addons[base_package].preferences

    kmi = km.keymap_items.new(idname='wm.call_panel', type=prefs.simple_export_panel_type, value='PRESS',
                              ctrl=prefs.simple_export_panel_ctrl, shift=prefs.simple_export_panel_shift,
                              alt=prefs.simple_export_panel_alt)
    add_key_to_keymap('POPUP_PT_simple_export', kmi, km, active=prefs.simple_export_panel_active)


def add_key_to_keymap(idname, kmi, km, active=True):
    """ Add ta key to the appropriate keymap """
    kmi.properties.name = idname
    kmi.active = active  # keys.append((km, kmi))


def remove_key(context, idname, properties_name):
    """Removes addon hotkeys from the keymap"""
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps['Window']

    for kmi in km.keymap_items:
        if kmi.idname == idname and kmi.properties.name == properties_name:
            km.keymap_items.remove(kmi)


def remove_keymap():
    """Removes keys from the keymap. Currently, this is only called when unregistering the addon. """
    # only works for menus and pie menus
    wm = bpy.context.window_manager
    km = wm.keyconfigs.addon.keymaps['Window']

    for kmi in km.keymap_items:
        if hasattr(kmi.properties, 'name') and kmi.properties.name in ['POPUP_PT_simple_export']:
            km.keymap_items.remove(kmi)



class REMOVE_OT_hotkey(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "simple_export.remove_hotkey"
    bl_label = "Remove hotkey"
    bl_description = "Remove hotkey"
    bl_options = {'REGISTER', 'INTERNAL'}

    idname: bpy.props.StringProperty()
    properties_name: bpy.props.StringProperty()
    property_prefix: bpy.props.StringProperty()

    def execute(self, context):
        remove_key(context, self.idname, self.properties_name)

        prefs = context.preferences.addons[base_package].preferences
        setattr(prefs, f'{self.property_prefix}_type', "NONE")
        setattr(prefs, f'{self.property_prefix}_ctrl', False)
        setattr(prefs, f'{self.property_prefix}_shift', False)
        setattr(prefs, f'{self.property_prefix}_alt', False)

        return {'FINISHED'}
