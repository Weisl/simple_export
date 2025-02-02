import bpy

from .. import __package__ as base_package


# Define a function to draw the custom menu item
def draw_custom_outliner_menu(self, context):
    layout = self.layout
    layout.separator()

    # Check if the active element is a collection
    layout.menu(CUSTOM_MT_outliner_simple_export_menu.bl_idname, icon='EXPORT')


class CUSTOM_MT_outliner_simple_export_menu(bpy.types.Menu):
    bl_label = "Simple Export"
    bl_idname = "CUSTOM_MT_outliner_simple_export_menu"

    def draw(self, context):
        layout = self.layout
        collection = context.collection

        # Add your custom menu items here
        layout.operator('simple_export.add_settings_to_collection', icon='COLLECTION_COLOR_01')

        # Determine the icon based on the collection's color_tag
        color_tag = collection.color_tag
        from .uilist import COLOR_TAG_ICONS
        icon = COLOR_TAG_ICONS.get(color_tag, 'OUTLINER_COLLECTION')

        layout.separator()
        op = layout.operator("simple_export.export_selected_collections", icon='EXPORT')
        op.outliner = True

        op = layout.operator("simple_export.assign_preset_selection", icon='PRESET_NEW')
        op.outliner = True

        op = layout.operator("scene.set_export_path_selection", text="Assign Filepaths", icon='FOLDER_REDIRECT')
        op.outliner = True

        # Open Popup window
        layout.operator("wm.call_panel", text="Open Export Popup",
                        icon='WINDOW').name = "SIMPLE_EXPORT_PT_simple_export_popup"


class EXPORTER_OT_open_preferences(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "simple_export.open_preferences"
    bl_label = "Open Addon preferences"

    addon_name: bpy.props.StringProperty()
    prefs_tabs: bpy.props.StringProperty()

    def execute(self, context):

        bpy.ops.screen.userpref_show()

        bpy.context.preferences.active_section = 'ADDONS'
        bpy.data.window_managers["WinMan"].addon_search = self.addon_name

        prefs = context.preferences.addons[base_package].preferences
        prefs.prefs_tabs = self.prefs_tabs

        import addon_utils
        mod = addon_utils.addons_fake_modules.get('simple_export')

        # mod is None the first time the operation is called :/
        if mod:
            mod.bl_info['show_expanded'] = True

            # Find User Preferences area and redraw it
            for window in context.window_manager.windows:
                for area in window.screen.areas:
                    if area.type == 'USER_PREFERENCES':
                        area.tag_redraw()

        bpy.ops.preferences.addon_expand(module=self.addon_name)
        return {'FINISHED'}


classes = (
    EXPORTER_OT_open_preferences,
    CUSTOM_MT_outliner_simple_export_menu
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    # Add outliner right click sub menu
    bpy.types.OUTLINER_MT_collection.append(draw_custom_outliner_menu)


def unregister():
    # Remove outliner right click sub menu
    bpy.types.OUTLINER_MT_collection.remove(draw_custom_outliner_menu)

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
