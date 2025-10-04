import bpy

from .. import __package__ as base_package

keymaps_items_dict = {"Simple Export Popup": {"name": 'simple_export_panel', "idname": 'wm.call_panel',
                                              "operator": 'SIMPLE_EXPORT_PT_simple_export_popup', "type": 'E',
                                              "value": 'PRESS', "ctrl": False, "shift": True, "alt": True,
                                              "active": True}, }


def add_key(context, idname, type, ctrl, shift, alt, operator, active):
    km = context.window_manager.keyconfigs.addon.keymaps.new(name="Window")

    kmi = km.keymap_items.new(idname=idname, type=type, value='PRESS', ctrl=ctrl, shift=shift, alt=alt)

    if operator != '':
        add_key_to_keymap(operator, kmi, active=active)


def remove_key(context, idname, properties_name):
    """Removes addon hotkeys from the keymap"""
    wm = context.window_manager
    addon_km = wm.keyconfigs.addon.keymaps.get('Window')
    user_km = wm.keyconfigs.user.keymaps.get('Window')
    if not addon_km:
        return

    items_to_remove = []
    for kmi in addon_km.keymap_items:
        if properties_name:
            if kmi.idname == idname and hasattr(kmi.properties, 'name') and kmi.properties.name == properties_name:
                items_to_remove.append(kmi)
        else:
            if kmi.idname == idname:
                items_to_remove.append(kmi)

    for kmi in items_to_remove:
        if user_km:
            user_kmi = user_km.keymap_items.find_match(addon_km, kmi)
            if user_kmi:
                user_km.keymap_items.remove(user_kmi)
        addon_km.keymap_items.remove(kmi)



def add_keymap():
    context = bpy.context
    prefs = context.preferences.addons[base_package].preferences
    wm = context.window_manager

    # Get or create the addon keymap
    addon_km = wm.keyconfigs.addon.keymaps.get('Window')
    if not addon_km:
        addon_km = wm.keyconfigs.addon.keymaps.new(name="Window")

    # Get or create the user keymap (for visibility in the Keymap Editor)
    user_km = wm.keyconfigs.user.keymaps.get('Window')
    if not user_km:
        user_km = wm.keyconfigs.user.keymaps.new(name="Window")

    # Clear existing keymap items for this addon
    for kmi in addon_km.keymap_items[:]:
        for key, valueDic in keymaps_items_dict.items():
            idname = valueDic["idname"]
            operator = valueDic["operator"]
            if kmi.idname == idname and (not operator or (hasattr(kmi.properties, 'name') and kmi.properties.name == operator)):
                addon_km.keymap_items.remove(kmi)

    # Add new keymap items
    for key, valueDic in keymaps_items_dict.items():
        idname = valueDic["idname"]
        type = getattr(prefs, f'{valueDic["name"]}_type')
        ctrl = getattr(prefs, f'{valueDic["name"]}_ctrl')
        shift = getattr(prefs, f'{valueDic["name"]}_shift')
        alt = getattr(prefs, f'{valueDic["name"]}_alt')
        operator = valueDic["operator"]
        active = valueDic["active"]

        # Skip if no key is assigned
        if type == 'NONE':
            continue

        # Add to addon keymap
        kmi = addon_km.keymap_items.new(
            idname=idname,
            type=type,
            value='PRESS',
            ctrl=ctrl,
            shift=shift,
            alt=alt
        )
        if operator != '':
            kmi.properties.name = operator
        kmi.active = active

        # Add to user keymap for visibility
        user_kmi = user_km.keymap_items.new(
            idname=idname,
            type=type,
            value='PRESS',
            ctrl=ctrl,
            shift=shift,
            alt=alt
        )
        if operator != '':
            user_kmi.properties.name = operator
        user_kmi.active = active


def add_key_to_keymap(idname, kmi, active=True):
    """ Add ta key to the appropriate keymap """
    kmi.properties.name = idname
    kmi.active = active


def remove_keymap():
    wm = bpy.context.window_manager
    addon_km = wm.keyconfigs.addon.keymaps.get('Window')
    user_km = wm.keyconfigs.user.keymaps.get('Window')
    if not addon_km:
        return

    items_to_remove = []
    for kmi in addon_km.keymap_items:
        for key, valueDic in keymaps_items_dict.items():
            idname = valueDic["idname"]
            operator = valueDic["operator"]
            if kmi.idname == idname and (not operator or (hasattr(kmi.properties, 'name') and kmi.properties.name == operator)):
                items_to_remove.append(kmi)

    for kmi in items_to_remove:
        if user_km:
            user_kmi = user_km.keymap_items.find_match(addon_km, kmi)
            if user_kmi:
                user_km.keymap_items.remove(user_kmi)
        addon_km.keymap_items.remove(kmi)



class SIMPLE_EXPORT_OT_hotkey(bpy.types.Operator):
    """Remove a hotkey and reset its properties"""
    bl_idname = "simple_export.remove_hotkey"
    bl_label = "Remove Hotkey"
    bl_description = "Remove the hotkey and reset its properties"
    bl_options = {'REGISTER', 'INTERNAL'}

    idname: bpy.props.StringProperty()
    properties_name: bpy.props.StringProperty()
    property_prefix: bpy.props.StringProperty()

    def execute(self, context):
        # Remove the hotkey from both addon and user keymaps
        wm = context.window_manager
        addon_km = wm.keyconfigs.addon.keymaps.get("Window")
        user_km = wm.keyconfigs.user.keymaps.get("Window")

        if addon_km:
            for kmi in addon_km.keymap_items[:]:
                if kmi.idname == self.idname and (not self.properties_name or (hasattr(kmi.properties, 'name') and kmi.properties.name == self.properties_name)):
                    addon_km.keymap_items.remove(kmi)

        if user_km:
            for kmi in user_km.keymap_items[:]:
                if kmi.idname == self.idname and (not self.properties_name or (hasattr(kmi.properties, 'name') and kmi.properties.name == self.properties_name)):
                    user_km.keymap_items.remove(kmi)

        # Reset the preferences
        prefs = context.preferences.addons[base_package].preferences
        setattr(prefs, f'{self.property_prefix}_type', "NONE")
        setattr(prefs, f'{self.property_prefix}_ctrl', False)
        setattr(prefs, f'{self.property_prefix}_shift', False)
        setattr(prefs, f'{self.property_prefix}_alt', False)

        # Force UI update
        for area in context.screen.areas:
            area.tag_redraw()

        return {'FINISHED'}



class SIMPLE_EXPORT_OT_change_key(bpy.types.Operator):
    """UI button to assign a new key to an addon hotkey"""
    bl_idname = "simple_export.key_selection_button"
    bl_label = "Press the button you want to assign to this operation."
    bl_options = {'REGISTER', 'INTERNAL'}

    property_prefix: bpy.props.StringProperty()

    def __init__(self):
        self.my_event = ''

    def invoke(self, context, event):
        prefs = context.preferences.addons[base_package].preferences
        self.prefs = prefs
        setattr(prefs, f'{self.property_prefix}_type', "NONE")

        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        self.my_event = 'NONE'

        if event.type and event.value == 'RELEASE':  # Apply
            self.my_event = event.type

            setattr(self.prefs, f'{self.property_prefix}_type', self.my_event)
            self.execute(context)
            return {'FINISHED'}

        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.report({'INFO'}, "Key change: " + bpy.types.Event.bl_rna.properties['type'].enum_items[self.my_event].name)
        return {'FINISHED'}


classes = (
    SIMPLE_EXPORT_OT_change_key,
    SIMPLE_EXPORT_OT_hotkey,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    add_keymap()


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)

    from .keymap import remove_keymap
    remove_keymap()
