import bpy

from .keymap import remove_key
from .panels import get_export_format_items


def add_key(self, km, idname, properties_name, simple_export_panel_type, simple_export_panel_ctrl,
            simple_export_panel_shift,
            simple_export_panel_alt, simple_export_panel_active):
    """
    Add a new keymap item to the specified keymap.

    Args:
        km (bpy.types.KeyMap): The keymap to which the new keymap item will be added.
        idname (str): The operator identifier.
        properties_name (str): The name property for the keymap item.
        simple_export_panel_type (str): The type of key (e.g., 'A', 'B', etc.).
        simple_export_panel_ctrl (bool): Whether the Ctrl key is pressed.
        simple_export_panel_shift (bool): Whether the Shift key is pressed.
        simple_export_panel_alt (bool): Whether the Alt key is pressed.
        simple_export_panel_active (bool): Whether the keymap item is active.

    Returns:
        None
    """
    kmi = km.keymap_items.new(idname=idname, type=simple_export_panel_type, value='PRESS',
                              ctrl=simple_export_panel_ctrl, shift=simple_export_panel_shift,
                              alt=simple_export_panel_alt)
    kmi.properties.name = properties_name
    kmi.active = simple_export_panel_active


# Scene properties to define search_path and replacement_path

def get_default_export_format():
    """Fetch default export format from add-on preferences or fallback to FBX."""
    try:
        return bpy.context.preferences.addons[__package__].preferences.default_export_format
    except (AttributeError, KeyError):
        return "FBX"  # Fallback default


def register_scene_properties():
    bpy.types.Scene.collection_index = bpy.props.IntProperty(
        name="Collection Index",
        description="Index of the active collection in the list",
        default=0
    )

    bpy.types.Scene.export_format = bpy.props.EnumProperty(
        name="Export Format",
        description="Filter collections by export format.",
        items=get_export_format_items(),
        default=get_default_export_format(),
    )


def register_collection_properties():
    bpy.types.Collection.simple_export_selected = bpy.props.BoolProperty(name="Selected Collection",
                                                                         description="Select this collection for export",
                                                                         default=False)

    bpy.types.Collection.offset_object = bpy.props.PointerProperty(name="Offset Object", type=bpy.types.Object,
                                                                   description="Object to be used for setting the collection offset")

    bpy.types.Collection.simple_export_selected = bpy.props.BoolProperty(name="Select for Export",
                                                                         description="Select this collection for export",
                                                                         default=False)


def unregister_scene_properties():
    del bpy.types.Scene.collection_index
    del bpy.types.Scene.export_format


def unregister_collection_properties():
    del bpy.types.Collection.simple_export_selected
    del bpy.types.Collection.offset_object


class SIMPLE_EXPORT_preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    def update_simple_export_panel_key(self, context):
        """
        Update the hotkey assignment for the collision pie menu.

        This function is called when the hotkey assignment is updated in the preferences.

        Args:
            context (bpy.types.Context): The current context.

        Returns:
            None
        """
        # This functions gets called when the hotkey assignment is updated in the preferences
        wm = bpy.context.window_manager
        km = wm.keyconfigs.addon.keymaps["Window"]
        simple_export_panel_type = self.simple_export_panel_type.upper()

        # Remove previous key assignment
        remove_key(context, 'wm.call_panel', "SIMPLE_EXPORT_PT_simple_export")
        add_key(self, km, 'wm.call_panel', "SIMPLE_EXPORT_PT_simple_export", simple_export_panel_type,
                self.simple_export_panel_ctrl,
                self.simple_export_panel_shift, self.simple_export_panel_alt, self.simple_export_panel_active)
        self.simple_export_panel_type = simple_export_panel_type

        return

    # Preference UI properties
    prefs_tabs: bpy.props.EnumProperty(
        name='Export Preferences',
        items=(('SETTINGS', "Settings", "General addon settings"),
               ('KEYMAP', "Keymap", "Change the hotkeys for tools associated with this addon.")),
        default='SETTINGS',
        description='Settings category:')

    # Main settings
    default_export_format: bpy.props.EnumProperty(
        name="Default Export Format",
        description="Default format for exporting collections.",
        items=get_export_format_items(),
        default="FBX",  # Default value
    )

    use_blender_file_location: bpy.props.BoolProperty(name="Use Blender File Location",
                                                      description="If checked, the export path will be set to the Blender file location. If unchecked, a custom path will be used.",
                                                      default=True)

    use_instance_offset: bpy.props.BoolProperty(name="(BETA) Move to Collection Offset",
                                                description="Use the collection offset for the exported collection",
                                                default=False)

    use_blend_file_name_as_prefix: bpy.props.BoolProperty(name="Use Blend File Name as Prefix",
                                                          description="If checked, the Blender file name will be used as a prefix for the export file name.",
                                                          default=False)

    ########################################
    # Filepath

    custom_export_path: bpy.props.StringProperty(name="Custom Export Path",
                                                 description="Custom directory to export files to.", subtype='DIR_PATH')

    ########################################
    # Collection Name

    custom_prefix: bpy.props.StringProperty(name="Custom Prefix",
                                            description="Custom prefix to add to the export file name.")

    custom_suffix: bpy.props.StringProperty(name="Custom Suffix",
                                            description="Custom suffix to add to the export file name.")

    search_path: bpy.props.StringProperty(name="Search Path", description="The path to be replaced.",
                                          default="workdata")
    replacement_path: bpy.props.StringProperty(name="Replacement Path", description="The path to replace with.",
                                               default="sourcedata")

    ########################################
    # Debug
    simple_export_debug: bpy.props.BoolProperty(name="Debug Mode",
                                                description="Debug mode only used for development",
                                                default=False)
    ########################################
    # Collections

    set_location_offset_on_creation: bpy.props.BoolProperty(name="Set Location Offset",
                                                            description="Set Location Offset",
                                                            default=True)

    collection_color: bpy.props.EnumProperty(
        name="Collection Color Tag",
        description="Choose a color tag for collections",
        items=[
            ('NONE', "Default", "Default color tag", 'OUTLINER_COLLECTION', 0),
            ('COLOR_01', "Color 1", "Red tag", 'COLLECTION_COLOR_01', 1),
            ('COLOR_02', "Color 2", "Orange tag", 'COLLECTION_COLOR_02', 2),
            ('COLOR_03', "Color 3", "Yellow tag", 'COLLECTION_COLOR_03', 3),
            ('COLOR_04', "Color 4", "Green tag", 'COLLECTION_COLOR_04', 4),
            ('COLOR_05', "Color 5", "Blue tag", 'COLLECTION_COLOR_05', 5),
            ('COLOR_06', "Color 6", "Purple tag", 'COLLECTION_COLOR_06', 6),
            ('COLOR_07', "Color 7", "Pink tag", 'COLLECTION_COLOR_07', 7),
            ('COLOR_08', "Color 8", "Gray tag", 'COLLECTION_COLOR_08', 8),
        ],
        default='NONE',
    )
    ###################################################################
    # Creation
    auto_set_filepath: bpy.props.BoolProperty(name="Use Filepath",
                                              description="Set filepath when creating an Exporter Collection",
                                              default=True)
    auto_set_preset: bpy.props.BoolProperty(name="Use Preset",
                                            description="Set export preset when creating an Exporter Collection",
                                            default=True)

    ###################################################################
    # KEYMAP

    simple_export_panel_type: bpy.props.StringProperty(name="Export Popup Menu", default="E",
                                                       update=update_simple_export_panel_key)

    simple_export_panel_ctrl: bpy.props.BoolProperty(name="Ctrl", default=False, update=update_simple_export_panel_key)

    simple_export_panel_shift: bpy.props.BoolProperty(name="Shift", default=True, update=update_simple_export_panel_key)
    simple_export_panel_alt: bpy.props.BoolProperty(name="Alt", default=True, update=update_simple_export_panel_key)

    simple_export_panel_active: bpy.props.BoolProperty(name="Active", default=True,
                                                       update=update_simple_export_panel_key)

    def keymap_ui(self, layout, title, property_prefix, id_name, properties_name):
        box = layout.box()
        split = box.split(align=True, factor=0.5)
        col = split.column()

        # Is hotkey active checkbox
        row = col.row(align=True)
        row.prop(self, f'{property_prefix}_active', text="")
        row.label(text=title)

        # Button to assign the key assignments
        col = split.column()
        row = col.row(align=True)
        key_type = getattr(self, f'{property_prefix}_type')
        text = (
            bpy.types.Event.bl_rna.properties['type'].enum_items[key_type].name
            if key_type != 'NONE'
            else 'Press a key'
        )

        op = row.operator("simple_export.key_selection_button", text=text)
        op.property_prefix = property_prefix

        # row.prop(self, f'{property_prefix}_type', text="")
        op = row.operator("simple_export.remove_hotkey", text="", icon="X")
        op.idname = id_name
        op.properties_name = properties_name
        op.property_prefix = property_prefix

        row = col.row(align=True)
        row.prop(self, f'{property_prefix}_ctrl')
        row.prop(self, f'{property_prefix}_shift')
        row.prop(self, f'{property_prefix}_alt')

    def draw(self, context):
        layout = self.layout

        row = layout.row(align=True)
        row.prop(self, "prefs_tabs", expand=True)

        if self.prefs_tabs == 'SETTINGS':
            layout.prop(self, "default_export_format")

            box = layout.box()
            box.label(text="Export Path")
            box.prop(self, "use_blender_file_location")
            if not self.use_blender_file_location:
                box.prop(self, "custom_export_path")
            box.prop(self, "search_path")
            box.prop(self, "replacement_path")

            box = layout.box()
            box.label(text="Export Collection Offset")

            # TODO: Set offset object

            box = layout.box()
            box.label(text="Export Collection")
            box.prop(self, "collection_color")
            # TODO: change prefix options from file to collections (- Better visibility)
            box.prop(self, "use_blend_file_name_as_prefix")
            box.prop(self, "custom_prefix")
            box.prop(self, "custom_suffix")
            # Collection offset
            box.prop(self, "set_location_offset_on_creation")
            # Collection offset
            box.prop(self, "auto_set_filepath")
            box.prop(self, "auto_set_preset")

            box = layout.box()
            box.label(text="Export Settings")
            box.prop(self, "use_instance_offset")

            layout.separator()
            layout.prop(self, "simple_export_debug")

        elif self.prefs_tabs == 'KEYMAP':
            self.keymap_ui(layout, 'Export Popup', 'simple_export_panel', 'wm.call_panel',
                           "SIMPLE_EXPORT_PT_simple_export")


# Initialize Window Manager Properties with Add-on Preferences Defaults

classes = (
    SIMPLE_EXPORT_preferences,
)


# Helper function to initialize Window Manager properties
def initialize_properties_collection_generation():
    prefs = bpy.context.preferences.addons[__package__].preferences

    bpy.types.WindowManager.custom_prefix = bpy.props.StringProperty(
        name="Custom Prefix",
        description="Custom prefix to add to the export file name.",
        default=prefs.custom_prefix
    )
    bpy.types.WindowManager.custom_suffix = bpy.props.StringProperty(
        name="Custom Suffix",
        description="Custom suffix to add to the export file name.",
        default=prefs.custom_suffix
    )
    bpy.types.WindowManager.use_blend_file_name_as_prefix = bpy.props.BoolProperty(
        name="Use Blend File Name as Prefix",
        description="If checked, the Blender file name will be used as a prefix for the export file name.",
        default=prefs.use_blend_file_name_as_prefix
    )
    bpy.types.WindowManager.set_location_offset_on_creation = bpy.props.BoolProperty(
        name="Set Location Offset",
        description="Set Location Offset",
        default=prefs.set_location_offset_on_creation
    )
    bpy.types.WindowManager.auto_set_filepath = bpy.props.BoolProperty(
        name="Use Filepath",
        description="Set filepath when creating an Exporter Collection",
        default=prefs.auto_set_filepath
    )
    bpy.types.WindowManager.auto_set_preset = bpy.props.BoolProperty(
        name="Use Preset",
        description="Set export preset when creating an Exporter Collection",
        default=prefs.auto_set_preset
    )


def initialize_properties_file_path():
    prefs = bpy.context.preferences.addons[__package__].preferences
    bpy.types.WindowManager.search_path = bpy.props.StringProperty(
        name="Search Path",
        description="The path to be replaced.",
        default=prefs.search_path
    )
    bpy.types.WindowManager.replacement_path = bpy.props.StringProperty(
        name="Replacement Path",
        description="The path to replace with.",
        default=prefs.replacement_path
    )


def post_register():
    initialize_properties_collection_generation()
    initialize_properties_file_path()


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    bpy.app.timers.register(post_register, first_interval=0.1)

    from .keymap import add_keymap
    add_keymap()
    register_scene_properties()
    register_collection_properties()


def unregister():
    from .keymap import remove_keymap
    remove_keymap()

    unregister_collection_properties()
    unregister_scene_properties()

    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    # Collection creation
    del bpy.types.WindowManager.custom_prefix
    del bpy.types.WindowManager.custom_suffix
    del bpy.types.WindowManager.use_blend_file_name_as_prefix

    # filepath
    del bpy.types.WindowManager.search_path
    del bpy.types.WindowManager.replacement_path
