import os
import textwrap

import bpy
from bpy.props import BoolProperty, PointerProperty

from .keymap import remove_key
from .panels import EXPORT_FORMATS
from .panels import get_export_format_items

PROPERTY_METADATA = {
    "custom_prefix": {
        "name": "Prefix",
        "description": "Custom prefix to add to the export file name.",
        "default": "",
    },
    "custom_suffix": {
        "name": "Suffix",
        "description": "Custom suffix to add to the export file name.",
        "default": "",
    },
    "use_blend_file_name_as_prefix": {
        "name": "File Name",
        "description": "If checked, the Blender file name will be used as a prefix for the export file name.",
        "default": False,
    },
    "search_path": {
        "name": "Search",
        "description": "The path to be replaced.",
        "default": "workdata",
    },
    "replacement_path": {
        "name": "Replace",
        "description": "The path to replace with.",
        "default": "sourcedata",
    },
    "collection_color": {
        "name": "Color",
        "description": "Choose a color tag for collections.",
        "items": [
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
        "default": 'NONE',
    },
    "auto_set_filepath": {
        "name": "Export Path",
        "description": "##### Set filepath when creating an Exporter Collection.",
        "default": True,
    },
    "auto_set_preset": {
        "name": "Export Preset",
        "description": "Set export preset when creating an Exporter Collection.",
        "default": True,
    },
    "set_location_offset_on_creation": {
        "name": "Collection Offset",
        "description": "Set Location Offset for collections.",
        "default": True,
    },
    "move_to_origin": {
        "name": "Move To Origin",
        "description": "Objects are moved to the origin based on the Collection Offset before exporting.",
        "default": False,
    },

    "use_custom_export_folder": {
        "name": "Custom Folder",
        "description": "Use a custom export folder",
        "default": False,
    },
    "custom_export_path": {
        "name": "Export Folder",
        "description": "Custom folder to export files to.",
        "default": '',
    },
}


def label_multiline(context, text, parent):
    chars = int(context.region.width / 7)  # 7 pix on 1 character
    wrapper = textwrap.TextWrapper(width=chars)
    text_lines = wrapper.wrap(text=text)
    for text_line in text_lines:
        parent.label(text=text_line)


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


class UIListProperties(bpy.types.PropertyGroup):
    uilist_icon: BoolProperty(
        name="Show Icon",
        description="Toggle visibility of the icon in the UI list",
        default=True
    )
    uilist_show_filepath: BoolProperty(
        name="Show Filepath",
        description="Toggle visibility of the filepath in the UI list",
        default=True
    )
    uilist_set_filepath: BoolProperty(
        name="Show Set Filepath",
        description="Toggle visibility of the filepath in the UI list",
        default=True
    )
    uilist_set_preset: BoolProperty(
        name="Show Preset",
        description="Toggle visibility of the preset in the UI list",
        default=True
    )


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
        wm = context.window_manager
        km = wm.keyconfigs.addon.keymaps["Window"]
        simple_export_panel_type = self.simple_export_panel_type.upper()

        # Remove previous key assignment
        remove_key(context, 'wm.call_panel', "SIMPLE_EXPORT_PT_simple_export_popup")
        add_key(self, km, 'wm.call_panel', "SIMPLE_EXPORT_PT_simple_export_popup", simple_export_panel_type,
                self.simple_export_panel_ctrl,
                self.simple_export_panel_shift, self.simple_export_panel_alt, self.simple_export_panel_active)
        self.simple_export_panel_type = simple_export_panel_type

        return

    # Preference UI properties
    prefs_tabs: bpy.props.EnumProperty(
        name='Export Preferences',
        items=(('SETTINGS', "Settings", "General addon settings"),
               ('UI', "UI", "Settings related to the UI."),
               ('KEYMAP', "Keymap", "Change the hotkeys for tools associated with this addon."),),
        default='SETTINGS',
        description='Settings category:'
    )

    # Main settings
    default_export_format: bpy.props.EnumProperty(
        name="Default Export Format",
        description="Default format for exporting collections.",
        items=get_export_format_items(),
        default="FBX",  # Default value
    )

    move_to_origin: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["move_to_origin"]["name"],
        description=PROPERTY_METADATA["move_to_origin"]["description"],
        default=PROPERTY_METADATA["move_to_origin"]["default"],
    )

    use_blend_file_name_as_prefix: bpy.props.BoolProperty(
        name="Use Blend File Name as Prefix",
        description="If checked, the Blender file name will be used as a prefix for the export file name.",
        default=False
    )

    ########################################
    # Filepath
    use_custom_export_folder: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["use_custom_export_folder"]["name"],
        description=PROPERTY_METADATA["use_custom_export_folder"]["description"],
        default=PROPERTY_METADATA["use_custom_export_folder"]["default"],
    )

    custom_export_path: bpy.props.StringProperty(
        name=PROPERTY_METADATA["custom_export_path"]["name"],
        description=PROPERTY_METADATA["custom_export_path"]["description"],
        default=PROPERTY_METADATA["custom_export_path"]["default"],
        subtype='DIR_PATH')

    search_path: bpy.props.StringProperty(
        name=PROPERTY_METADATA["search_path"]["name"],
        description=PROPERTY_METADATA["search_path"]["description"],
        default=PROPERTY_METADATA["search_path"]["default"],
    )

    replacement_path: bpy.props.StringProperty(
        name=PROPERTY_METADATA["replacement_path"]["name"],
        description=PROPERTY_METADATA["replacement_path"]["description"],
        default=PROPERTY_METADATA["replacement_path"]["default"],
    )

    ########################################
    # Collection Name

    custom_prefix: bpy.props.StringProperty(
        name=PROPERTY_METADATA["custom_prefix"]["name"],
        description=PROPERTY_METADATA["custom_prefix"]["description"],
        default=PROPERTY_METADATA["custom_prefix"]["default"],
    )

    custom_suffix: bpy.props.StringProperty(
        name=PROPERTY_METADATA["custom_suffix"]["name"],
        description=PROPERTY_METADATA["custom_suffix"]["description"],
        default=PROPERTY_METADATA["custom_suffix"]["default"],
    )

    ########################################
    # Collections

    set_location_offset_on_creation: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["set_location_offset_on_creation"]["name"],
        description=PROPERTY_METADATA["set_location_offset_on_creation"]["description"],
        default=PROPERTY_METADATA["set_location_offset_on_creation"]["default"],
    )

    collection_color: bpy.props.EnumProperty(
        name=PROPERTY_METADATA["collection_color"]["name"],
        description=PROPERTY_METADATA["collection_color"]["description"],
        items=PROPERTY_METADATA["collection_color"]["items"],
        default=PROPERTY_METADATA["collection_color"]["default"],
    )

    auto_set_filepath: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["auto_set_filepath"]["name"],
        description=PROPERTY_METADATA["auto_set_filepath"]["description"],
        default=PROPERTY_METADATA["auto_set_filepath"]["default"],
    )

    auto_set_preset: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["auto_set_preset"]["name"],
        description=PROPERTY_METADATA["auto_set_preset"]["description"],
        default=PROPERTY_METADATA["auto_set_preset"]["default"],
    )
    ###################################################################
    # KEYMAP

    simple_export_panel_type: bpy.props.StringProperty(
        name="Export Popup Menu", default="E",
        update=update_simple_export_panel_key)

    simple_export_panel_ctrl: bpy.props.BoolProperty(
        name="Ctrl", default=False, update=update_simple_export_panel_key)

    simple_export_panel_shift: bpy.props.BoolProperty(
        name="Shift", default=True, update=update_simple_export_panel_key)
    simple_export_panel_alt: bpy.props.BoolProperty(
        name="Alt", default=True, update=update_simple_export_panel_key)

    simple_export_panel_active: bpy.props.BoolProperty(
        name="Active", default=True,
        update=update_simple_export_panel_key)

    ########################################
    # Debug
    simple_export_debug: bpy.props.BoolProperty(name="Debug Mode",
                                                description="Debug mode only used for development",
                                                default=False)

    ########################################
    # UI
    report_errors_only: bpy.props.BoolProperty(name="Report Errors Only",
                                               description="Show the result panel only when errors occur.",
                                               default=False)

    scene_properties: PointerProperty(type=UIListProperties)
    popup_properties: PointerProperty(type=UIListProperties)

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

        layout.separator()

        if self.prefs_tabs == 'SETTINGS':
            layout.prop(self, "default_export_format")

            # Iterate through dynamically created properties
            box = layout.box()
            for export_format in EXPORT_FORMATS.keys():
                prop_name = f"simple_export_preset_file_{export_format.lower()}"
                if hasattr(bpy.types.WindowManager, prop_name):
                    row = box.row(align=True)
                    row.label(text=f"{export_format} Preset", icon='FILE_SCRIPT')
                    row.prop(context.window_manager, prop_name, text="")

            box = layout.box()
            box.label(text="Export Path")
            box.prop(self, "use_custom_export_folder")
            if self.use_custom_export_folder:
                box.prop(self, "custom_export_path")
            if not self.use_custom_export_folder:
                texts = []
                texts.append("Export Path is set relative to the .blend file directory.")
                texts.append("Use Search and Replace to manipulate the path")

                for text in texts:
                    label_multiline(
                        context=context,
                        text=text,
                        parent=box
                    )

                box.prop(self, "search_path")
                box.prop(self, "replacement_path")

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
            box.label(text="Pre Export Operations")
            box.prop(self, "move_to_origin")

            layout.separator()
            layout.prop(self, "simple_export_debug", icon='WARNING_LARGE')

        elif self.prefs_tabs == 'UI':

            layout.prop(self, "report_errors_only")

            box = layout.box()
            box.label(text="Scene List")
            box.prop(self.scene_properties, "uilist_icon")
            box.prop(self.scene_properties, "uilist_show_filepath")
            box.prop(self.scene_properties, "uilist_set_filepath")
            box.prop(self.scene_properties, "uilist_set_preset")

            box = layout.box()
            box.label(text="Popup List")
            box.prop(self.popup_properties, "uilist_icon")
            box.prop(self.popup_properties, "uilist_show_filepath")
            box.prop(self.popup_properties, "uilist_set_filepath")
            box.prop(self.popup_properties, "uilist_set_preset")

        elif self.prefs_tabs == 'KEYMAP':
            self.keymap_ui(layout, 'Export Popup', 'simple_export_panel', 'wm.call_panel',
                           "SIMPLE_EXPORT_PT_simple_export_popup")


# Initialize Window Manager Properties with Add-on Preferences Defaults

classes = (
    UIListProperties,
    SIMPLE_EXPORT_preferences,
)


def update_preset_path(self, context):
    self.preset_path = EXPORT_FORMATS[self.export_format]["preset_folder"]


def get_default_export_format():
    """Fetch default export format from add-on preferences or fallback to FBX."""
    try:
        return bpy.context.preferences.addons[__package__].preferences.default_export_format
    except (AttributeError, KeyError):
        print('Fallback to FBX')
        return "FBX"  # Fallback default


def update_scene_preset_path(self, context):
    """Update the full path of the selected preset in the scene property."""
    try:
        prop_name = f"simple_export_preset_file_{context.window_manager.export_format.lower()}"
        selected_preset = getattr(context.window_manager, prop_name, None)

        # Debug output
        print(f"[DEBUG] Updating preset path for: {prop_name}")
        print(f"[DEBUG] Selected preset: {selected_preset}")

        if selected_preset:
            context.scene.simple_export_preset_file = selected_preset
            self.report({'INFO'}, f"Preset path updated to: {selected_preset}")
        else:
            self.report({'WARNING'}, "No preset selected or preset path is invalid.")
    except Exception as e:
        # Debug error handling
        print(f"[DEBUG ERROR] Failed to update preset path: {e}")
        self.report({'ERROR'}, f"Failed to update preset path: {e}")


def get_py_files(self=None, context=None, folder=None):
    """Retrieve all .py files from the specified folder."""
    if folder is None:
        # Fallback to the preset folder logic
        preset_path = None
        if self is not None:  # Check if self is provided and has a preset_path attribute
            preset_path = getattr(self, 'preset_path', None)

        if not preset_path:  # If preset_path is still None, use a fallback
            preset_path = bpy.context.preferences.addons[__package__].preferences.preset_path

        folder = preset_path

    if not folder or not os.path.isdir(folder):
        print(f"[DEBUG] Invalid folder: {folder}")
        return [("", "No Path", "No path specified")]

    try:
        files = [
            (os.path.join(folder, f), f, "")
            for f in os.listdir(folder)
            if f.endswith(".py")
        ]
        print(f"[DEBUG] Files found in {folder}: {files}")
        return files if files else [("", "No Files", "No .py files found")]
    except Exception as e:
        print(f"[DEBUG ERROR] Error reading files in {folder}: {e}")
        return [("", "Error", str(e))]


from functools import partial


def get_py_files_for_format(self, context, folder):
    """Retrieve all .py files from the specified folder for the given export format."""
    return get_py_files(self, context, folder)


def create_export_format_preset_properties():
    """
    Dynamically create individual preset properties for each export format.
    """
    for export_format, format_details in EXPORT_FORMATS.items():
        prop_name = f"simple_export_preset_file_{export_format.lower()}"
        preset_folder = format_details.get("preset_folder", "")

        # Ensure the folder exists and provide debug information
        if not os.path.isdir(preset_folder):
            print(f"[DEBUG] Invalid folder for {export_format}: {preset_folder}")
            continue

        print(f"[DEBUG] Creating property: {prop_name} for folder: {preset_folder}")

        # Use a function to bind the current preset_folder to the property
        def create_property(folder):
            def get_py_files_for_this_format(self, context):
                """Retrieve .py files specifically for this export format."""
                return get_py_files(self, context, folder)

            def update_preset_path_for_this_format(self, context):
                try:
                    selected_preset = getattr(self, prop_name, None)
                    if selected_preset:
                        setattr(context.scene, f"simple_export_preset_path_{export_format.lower()}", selected_preset)
                        print(f"[DEBUG] Updated preset path for {export_format}: {selected_preset}")
                except Exception as e:
                    print(f"[DEBUG ERROR] Failed to update preset path for {export_format}: {e}")

            # Create the property dynamically
            return bpy.props.EnumProperty(
                name=f"{export_format} Preset File",
                description=f"Select a preset file for {export_format}",
                items=lambda self, context: get_py_files_for_this_format(self, context),
                update=update_preset_path_for_this_format,
            )

        # Set the property dynamically with the current folder
        setattr(bpy.types.WindowManager, prop_name, create_property(preset_folder))


def initialize_format_specific_properties():
    """
    Initialize format-specific properties on addon registration.
    """
    create_export_format_preset_properties()


# Helper function to initialize Window Manager properties
def initialize_properties_collection_generation():
    prefs = bpy.context.preferences.addons[__package__].preferences

    bpy.types.WindowManager.export_format = bpy.props.EnumProperty(
        name="Export Format",
        description="Select the export format",
        items=get_export_format_items(),  # Dynamically generated items from EXPORT_FORMATS
        default=get_default_export_format(),
        update=update_preset_path,  # Update the preset path when export format changes
    )

    bpy.types.WindowManager.simple_export_preset_file = bpy.props.EnumProperty(
        name="Preset File",
        description="Select a .py file",
        items=lambda self, context: get_py_files(self),  # Pass self explicitly
        update=update_scene_preset_path,
    )

    bpy.types.WindowManager.override_path = bpy.props.BoolProperty(
        name="Overwrite Preset Folder",
        description="Manually override the automatically set preset folder",
        default=False,
    )

    bpy.types.WindowManager.preset_path = bpy.props.StringProperty(
        name="Preset Folder Path",
        description="Path to the folder containing .py files",
        default=EXPORT_FORMATS["FBX"]["preset_folder"],  # Dynamically fetch from EXPORT_FORMATS
        subtype="DIR_PATH",
    )

    bpy.types.WindowManager.custom_prefix = bpy.props.StringProperty(
        name=PROPERTY_METADATA["custom_prefix"]["name"],
        description=PROPERTY_METADATA["custom_prefix"]["description"],
        default=prefs.custom_prefix
    )
    bpy.types.WindowManager.custom_suffix = bpy.props.StringProperty(
        name=PROPERTY_METADATA["custom_suffix"]["name"],
        description=PROPERTY_METADATA["custom_suffix"]["description"],
        default=prefs.custom_suffix
    )
    bpy.types.WindowManager.use_blend_file_name_as_prefix = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["use_blend_file_name_as_prefix"]["name"],
        description=PROPERTY_METADATA["use_blend_file_name_as_prefix"]["description"],
        default=prefs.use_blend_file_name_as_prefix
    )
    bpy.types.WindowManager.set_location_offset_on_creation = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["set_location_offset_on_creation"]["name"],
        description=PROPERTY_METADATA["set_location_offset_on_creation"]["description"],
        default=prefs.set_location_offset_on_creation
    )
    bpy.types.WindowManager.move_to_origin = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["move_to_origin"]["name"],
        description=PROPERTY_METADATA["move_to_origin"]["description"],
        default=prefs.move_to_origin,
    )

    bpy.types.WindowManager.auto_set_filepath = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["auto_set_filepath"]["name"],
        description=PROPERTY_METADATA["auto_set_filepath"]["description"],
        default=prefs.auto_set_filepath
    )
    bpy.types.WindowManager.auto_set_preset = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["auto_set_preset"]["name"],
        description=PROPERTY_METADATA["auto_set_preset"]["description"],
        default=prefs.auto_set_preset
    )
    bpy.types.WindowManager.collection_color = bpy.props.EnumProperty(
        name=PROPERTY_METADATA["collection_color"]["name"],
        description=PROPERTY_METADATA["collection_color"]["description"],
        items=PROPERTY_METADATA["collection_color"]["items"],
        default=prefs.collection_color
    )


def initialize_properties_file_path():
    prefs = bpy.context.preferences.addons[__package__].preferences

    bpy.types.WindowManager.search_path = bpy.props.StringProperty(
        name=PROPERTY_METADATA["search_path"]["name"],
        description=PROPERTY_METADATA["search_path"]["description"],
        default=prefs.search_path
    )
    bpy.types.WindowManager.replacement_path = bpy.props.StringProperty(
        name=PROPERTY_METADATA["replacement_path"]["name"],
        description=PROPERTY_METADATA["replacement_path"]["description"],
        default=prefs.replacement_path
    )
    bpy.types.WindowManager.use_custom_export_folder = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["use_custom_export_folder"]["name"],
        description=PROPERTY_METADATA["use_custom_export_folder"]["description"],
        default=prefs.use_custom_export_folder
    )
    bpy.types.WindowManager.custom_export_path = bpy.props.StringProperty(
        name="Custom Export Path",
        description="Custom directory to export files to.",
        subtype='DIR_PATH',
        default=prefs.custom_export_path
    )


def post_register():
    initialize_properties_collection_generation()
    initialize_properties_file_path()


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    from .keymap import add_keymap
    add_keymap()

    bpy.types.Scene.collection_index = bpy.props.IntProperty(
        name="Collection Index",
        description="Index of the active collection in the list",
        default=0
    )

    bpy.types.WindowManager.overwrite_collection_settings = bpy.props.BoolProperty(
        name="Overwrite Collection",
        description="Overwrite the settings related to the creation of Export Collections defined in the Preferences",
        default=False)

    bpy.types.WindowManager.overwrite_filepath_settings = bpy.props.BoolProperty(
        name="Overwrite Filepath",
        description="Overwrite the settings regarding the generation of the export path defined in the Preferences",
        default=False)

    bpy.types.Collection.simple_export_selected = bpy.props.BoolProperty(
        name="Selected Collection",
        description="Select this collection for export",
        default=False)

    bpy.types.Collection.offset_object = bpy.props.PointerProperty(
        name="Offset Object", type=bpy.types.Object,
        description="Object to be used for setting the collection offset")

    bpy.types.Collection.simple_export_selected = bpy.props.BoolProperty(
        name="Select for Export",
        description="Select this collection for export",
        default=False)

    bpy.app.timers.register(post_register, first_interval=0.1)
    initialize_format_specific_properties()


def unregister():
    from .keymap import remove_keymap
    remove_keymap()

    # Remove dynamically created properties
    for export_format in EXPORT_FORMATS.keys():
        prop_name = f"simple_export_preset_file_{export_format.lower()}"
        if hasattr(bpy.types.WindowManager, prop_name):
            delattr(bpy.types.WindowManager, prop_name)

    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    # Persistant settings
    del bpy.types.Scene.collection_index
    del bpy.types.Scene.export_format
    del bpy.types.Collection.simple_export_selected
    del bpy.types.Collection.offset_object

    del bpy.types.WindowManager.overwrite_filepath_settings
    del bpy.types.WindowManager.overwrite_collection_settings

    # Collection creation
    del bpy.types.WindowManager.custom_prefix
    del bpy.types.WindowManager.custom_suffix
    del bpy.types.WindowManager.use_blend_file_name_as_prefix
    del bpy.types.WindowManager.set_location_offset_on_creation
    del bpy.types.WindowManager.auto_set_filepath
    del bpy.types.WindowManager.auto_set_preset
    del bpy.types.WindowManager.collection_color

    # filepath
    del bpy.types.WindowManager.search_path
    del bpy.types.WindowManager.replacement_path
    del bpy.types.WindowManager.use_custom_export_folder
    del bpy.types.WindowManager.custom_export_path
