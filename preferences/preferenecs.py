import os

import bpy
from bpy.props import BoolProperty, PointerProperty

from .keymap import remove_key
from .. import __package__ as base_package
from ..core.export_formats import ExportFormats
from ..core.export_formats import get_export_format_items
from ..ui.n_panel import VIEW3D_PT_SimpleExport

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
    "mirror_search_path": {
        "name": "Search",
        "description": "The path to be replaced.",
        "default": "workdata",
    },
    "mirror_replacement_path": {
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
        "default": False,
    },
    "move_by_collection_offset": {
        "name": "Move by Collection Offset",
        "description": "Objects are moved to the origin based on the Collection Offset before exporting.",
        "default": False,
    },

    "export_folder_mode": {
        "name": "Custom Export Path Mode",
        "description": "Choose how the export file path is determined",
        "default": "ABSOLUTE",
        "items": [
            ("ABSOLUTE", "Absolute", "Use an absolute file path"),
            ("RELATIVE", "Relative", "Use a file path relative to the .blend file"),
            ("MIRROR", "Mirror", "Mirror part of the blend file path with another directory"),
        ],
    },

    "absolute_export_path": {
        "name": "Export Folder",
        "description": "Custom absolute folder to export files to.",
        "default": '',
    },

    "relative_export_path": {
        "name": "Relative Folder Path",
        "description": "Folder to export files relative to the .blend file.",
        "default": '',
    },
}


# Wrapper functions for each format using the existing `get_py_files` function
def get_py_files_for_fbx(self, context):
    export_format = ExportFormats.get("FBX")
    return get_py_files(self, context, export_format.preset_folder if export_format else None)


def get_py_files_for_obj(self, context):
    export_format = ExportFormats.get("OBJ")
    return get_py_files(self, context, export_format.preset_folder if export_format else None)


def get_py_files_for_gltf(self, context):
    export_format = ExportFormats.get("GLTF")
    return get_py_files(self, context, export_format.preset_folder if export_format else None)


def get_py_files_for_usd(self, context):
    export_format = ExportFormats.get("USD")
    return get_py_files(self, context, export_format.preset_folder if export_format else None)


def get_py_files_for_abc(self, context):
    export_format = ExportFormats.get("ABC")
    return get_py_files(self, context, export_format.preset_folder if export_format else None)


def get_py_files_for_ply(self, context):
    export_format = ExportFormats.get("PLY")
    return get_py_files(self, context, export_format.preset_folder if export_format else None)


def get_py_files_for_stl(self, context):
    export_format = ExportFormats.get("STL")
    return get_py_files(self, context, export_format.preset_folder if export_format else None)


def update_preset_path_for_fbx(self, context):
    context.scene.simple_export_preset_file_fbx = self.simple_export_preset_file_fbx


def update_preset_path_for_obj(self, context):
    context.scene.simple_export_preset_file_obj = self.simple_export_preset_file_obj


def update_preset_path_for_gltf(self, context):
    context.scene.simple_export_preset_file_gltf = self.simple_export_preset_file_gltf


def update_preset_path_for_usd(self, context):
    context.scene.simple_export_preset_file_usd = self.simple_export_preset_file_usd


def update_preset_path_for_abc(self, context):
    context.scene.simple_export_preset_file_abc = self.simple_export_preset_file_abc


def update_preset_path_for_ply(self, context):
    context.scene.simple_export_preset_file_ply = self.simple_export_preset_file_ply


def update_preset_path_for_stl(self, context):
    context.scene.simple_export_preset_file_stl = self.simple_export_preset_file_stlF


def update_panel_category(self, context):
    """Update panel tab for simple export"""
    panels = [
        VIEW3D_PT_SimpleExport,
    ]

    for panel in panels:
        try:
            bpy.utils.unregister_class(panel)
        except:
            pass

        prefs = context.preferences.addons[base_package].preferences
        panel.bl_category = prefs.panel_category

        if prefs.enable_n_panel:
            try:
                bpy.utils.register_class(panel)
            except ValueError:
                pass  # Avoid duplicate registrations
    return


def update_mirror_preview(self, context):
    """Update preview when mirror settings change."""
    compute_mirror_preview(self)  # Pass scene as settings


def compute_mirror_preview(settings):
    """Compute the final mirrored path and return it for display."""
    blend_path = bpy.path.abspath("//")  # Get the blend file directory

    # Ensure search path is valid
    if not settings.mirror_search_path or not settings.mirror_replacement_path:
        return "Invalid search/replacement paths"

    # Ensure blend file path contains the search path before replacing
    if settings.mirror_search_path in blend_path:
        export_path = blend_path.replace(settings.mirror_search_path, settings.mirror_replacement_path)
        return bpy.path.relpath(export_path) if "//" in export_path else export_path

    return "Search path not found in blend file path"


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


# Scene properties to define mirror_search_path and mirror_replacement_path


import bpy
import os

import bpy
import os


def get_relative_path(instance):
    """Ensure the stored path is always relative to the .blend file."""
    if isinstance(instance, bpy.types.AddonPreferences):
        # If called from AddonPreferences
        stored_path = instance.get("relative_export_path", "")
    elif isinstance(instance, bpy.types.Scene):
        # If called from Scene (fallback)
        stored_path = instance.get("relative_export_path", "")
    else:
        return ""

    if stored_path:
        return bpy.path.relpath(stored_path)  # Use Blender's built-in function
    return ""


def set_relative_path(instance, value):
    """Convert any assigned path to a direct relative path."""
    blend_dir = bpy.path.abspath("//")  # Get absolute blend directory

    if not blend_dir:
        if isinstance(instance, bpy.types.AddonPreferences):
            instance["relative_export_path"] = value  # Store as-is
        elif isinstance(instance, bpy.types.Scene):
            instance["relative_export_path"] = value  # Store in scene
        return

    absolute_path = bpy.path.abspath(value)  # Convert input to absolute path

    try:
        # Use `os.path.relpath()` to ensure a clean direct relative path
        relative_path = os.path.relpath(absolute_path, blend_dir)
        formatted_path = f"//{relative_path.replace(os.sep, '/')}"

        if isinstance(instance, bpy.types.AddonPreferences):
            instance["relative_export_path"] = formatted_path
        elif isinstance(instance, bpy.types.Scene):
            instance["relative_export_path"] = formatted_path
    except ValueError:
        # Path is outside the blend directory, reset to empty
        if isinstance(instance, bpy.types.AddonPreferences):
            instance["relative_export_path"] = ""
        elif isinstance(instance, bpy.types.Scene):
            instance["relative_export_path"] = ""


def get_absolute_path(instance):
    """Ensure the stored path is always an absolute path."""
    if isinstance(instance, bpy.types.AddonPreferences):
        # If called from AddonPreferences
        stored_path = instance.get("absolute_export_path", "")
    elif isinstance(instance, bpy.types.Scene):
        # If called from Scene (fallback)
        stored_path = instance.get("absolute_export_path", "")
    else:
        return ""

    if stored_path:
        return bpy.path.abspath(stored_path)  # Convert to absolute path
    return ""

def set_absolute_path(instance, value):
    """Convert any assigned path to an absolute path."""
    absolute_path = bpy.path.abspath(value)  # Ensure absolute path format

    if isinstance(instance, bpy.types.AddonPreferences):
        instance["absolute_export_path"] = absolute_path
    elif isinstance(instance, bpy.types.Scene):
        instance["absolute_export_path"] = absolute_path


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
    bl_idname = base_package
    bl_options = {'REGISTER'}

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

    move_by_collection_offset: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["move_by_collection_offset"]["name"],
        description=PROPERTY_METADATA["move_by_collection_offset"]["description"],
        default=PROPERTY_METADATA["move_by_collection_offset"]["default"],
    )

    use_blend_file_name_as_prefix: bpy.props.BoolProperty(
        name="Use Blend File Name as Prefix",
        description="If checked, the Blender file name will be used as a prefix for the export file name.",
        default=False
    )

    ########################################
    # Filepath
    export_folder_mode: bpy.props.EnumProperty(
        name=PROPERTY_METADATA["export_folder_mode"]["name"],
        description=PROPERTY_METADATA["export_folder_mode"]["description"],
        items=PROPERTY_METADATA["export_folder_mode"]["items"],
        default=PROPERTY_METADATA["export_folder_mode"]["default"],
    )

    absolute_export_path: bpy.props.StringProperty(
        name=PROPERTY_METADATA["absolute_export_path"]["name"],
        description=PROPERTY_METADATA["absolute_export_path"]["description"],
        default=PROPERTY_METADATA["absolute_export_path"]["default"],
        subtype='DIR_PATH',
        get=get_absolute_path,  # Use shared absolute path getter
        set=set_absolute_path  # Use shared absolute path setter
    )

    relative_export_path: bpy.props.StringProperty(
        name=PROPERTY_METADATA["relative_export_path"]["name"],
        description=PROPERTY_METADATA["relative_export_path"]["description"],
        default=PROPERTY_METADATA["relative_export_path"]["default"],
        subtype='DIR_PATH',
        get=get_relative_path,  # Use the same getter
        set=set_relative_path  # Use the same setter
    )

    mirror_search_path: bpy.props.StringProperty(
        name=PROPERTY_METADATA["mirror_search_path"]["name"],
        description=PROPERTY_METADATA["mirror_search_path"]["description"],
        default=PROPERTY_METADATA["mirror_search_path"]["default"],
        update=update_mirror_preview,
    )

    mirror_replacement_path: bpy.props.StringProperty(
        name=PROPERTY_METADATA["mirror_replacement_path"]["name"],
        description=PROPERTY_METADATA["mirror_replacement_path"]["description"],
        default=PROPERTY_METADATA["mirror_replacement_path"]["default"],
        update=update_mirror_preview,
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
    npanel_properties: PointerProperty(type=UIListProperties)

    panel_category: bpy.props.StringProperty(name="Category Tab",
                                             description="The category name used to organize the addon in the properties panel for all the addons",
                                             default='Simple Exporter',
                                             update=update_panel_category)  # update = update_panel_position,

    enable_n_panel: bpy.props.BoolProperty(
        name="Enable Simple Export N-Panel",
        description="Toggle the N-Panel on and off.",
        default=True,
        update=update_panel_category)

    ########################################
    # Presets
    simple_export_preset_file_fbx: bpy.props.EnumProperty(
        name="FBX Preset File",
        description="Select a preset file for FBX",
        items=lambda self, context: get_py_files_for_fbx(self, context),
        update=update_preset_path_for_fbx,
    )

    simple_export_preset_file_obj: bpy.props.EnumProperty(
        name="OBJ Preset File",
        description="Select a preset file for OBJ",
        items=lambda self, context: get_py_files_for_obj(self, context),
        update=update_preset_path_for_obj,
    )

    simple_export_preset_file_gltf: bpy.props.EnumProperty(
        name="glTF Preset File",
        description="Select a preset file for glTF",
        items=lambda self, context: get_py_files_for_gltf(self, context),
        update=update_preset_path_for_gltf,
    )

    simple_export_preset_file_usd: bpy.props.EnumProperty(
        name="USD Preset File",
        description="Select a preset file for USD",
        items=lambda self, context: get_py_files_for_usd(self, context),
        update=update_preset_path_for_usd,
    )

    simple_export_preset_file_abc: bpy.props.EnumProperty(
        name="Alembic Preset File",
        description="Select a preset file for Alembic",
        items=lambda self, context: get_py_files_for_abc(self, context),
        update=update_preset_path_for_abc,
    )

    simple_export_preset_file_ply: bpy.props.EnumProperty(
        name="PLY Preset File",
        description="Select a preset file for PLY",
        items=lambda self, context: get_py_files_for_ply(self, context),
        update=update_preset_path_for_ply,
    )

    simple_export_preset_file_stl: bpy.props.EnumProperty(
        name="STL Preset File",
        description="Select a preset file for STL",
        items=lambda self, context: get_py_files_for_stl(self, context),
        update=update_preset_path_for_stl,
    )

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
            box.label(text="Export Presets")

            # Use ExportFormats to get all available formats
            for export_format in ExportFormats.FORMATS.keys():
                prop_name = f"simple_export_preset_file_{export_format.lower()}"

                if hasattr(self, prop_name):
                    row = box.row(align=True)
                    row.label(text=f"{export_format} Preset", icon='FILE_SCRIPT')
                    row.prop(self, prop_name, text="")

            box = layout.box()
            box.label(text="Export Path")
            row = box.row()
            row.prop(self, "export_folder_mode", expand=True)

            if self.export_folder_mode == 'ABSOLUTE':
                box.prop(self, "absolute_export_path")

            if self.export_folder_mode == 'RELATIVE':
                box.prop(self, "relative_export_path")

            if self.export_folder_mode == 'MIRROR':
                box.prop(self, "mirror_search_path", text="Search Path")
                box.prop(self, "mirror_replacement_path", text="Replacement Path")

                # Compute and display the preview
                preview_path = compute_mirror_preview(self)  # Pass `self` as settings
                preview_box = box.box()
                preview_box.label(text="Preview of Final Path:")
                preview_box.label(text=preview_path, icon='FILE_FOLDER')

            box = layout.box()
            box.label(text="Export Collection")
            box.prop(self, "collection_color")

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
            box.prop(self, "move_by_collection_offset")

            layout.separator()
            icon = 'WARNING_LARGE' if bpy.app.version >= (4, 3, 0) else 'ERROR'
            layout.prop(self, "simple_export_debug")

        elif self.prefs_tabs == 'UI':

            box = layout.box()
            box.label(text="N Panel")
            layout.prop(self, 'enable_n_panel')
            layout.prop(self, 'panel_category')
            box = box.box()
            box.prop(self.npanel_properties, "uilist_icon")
            box.prop(self.npanel_properties, "uilist_show_filepath")
            box.prop(self.npanel_properties, "uilist_set_filepath")
            box.prop(self.npanel_properties, "uilist_set_preset")

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

            box = layout.box()
            box.label(text="Warnings")
            box.prop(self, "report_errors_only")


        elif self.prefs_tabs == 'KEYMAP':
            self.keymap_ui(layout, 'Export Popup', 'simple_export_panel', 'wm.call_panel',
                           "SIMPLE_EXPORT_PT_simple_export_popup")


# Initialize Window Manager Properties with Add-on Preferences Defaults

classes = (
    UIListProperties,
    SIMPLE_EXPORT_preferences,
)


def update_preset_path(self, context):
    export_format = ExportFormats.get(self.export_format)

    if export_format:
        self.preset_path = export_format.preset_folder
    else:
        self.preset_path = ""  # Fallback in case the format is invalid


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

        if selected_preset:
            context.window_manager.simple_export_preset_file = selected_preset
            self.report({'INFO'}, f"Preset path updated to: {selected_preset}")
        else:
            self.report({'WARNING'}, "No preset selected or preset path is invalid.")
    except Exception as e:
        # Debug error handling
        # print(f"[DEBUG ERROR] Failed to update preset path: {e}")
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
        # print(f"[DEBUG] Invalid folder: {folder}")
        return [("", "Create Presets", "No path specified")]

    try:
        files = [
            (os.path.join(folder, f), f, "")
            for f in os.listdir(folder)
            if f.endswith(".py")
        ]
        # print(f"[DEBUG] Files found in {folder}: {files}")
        return files if files else [("", "No Files", "No .py files found")]
    except Exception as e:
        # print(f"[DEBUG ERROR] Error reading files in {folder}: {e}")
        return [("", "Error", str(e))]


def create_export_format_preset_properties():
    """
    Dynamically create individual preset properties for each export format.
    """
    for export_format_key, export_format in ExportFormats.FORMATS.items():
        prop_name = f"simple_export_preset_file_{export_format_key.lower()}"
        preset_folder = export_format.preset_folder

        # Ensure the folder exists and provide debug information
        if not os.path.isdir(preset_folder):
            # print(f"[DEBUG] Invalid folder for {export_format_key}: {preset_folder}")
            continue

        # print(f"[DEBUG] Creating property: {prop_name} for folder: {preset_folder}")

        # Use a function to bind the current preset_folder to the property
        def create_property(folder):
            def get_py_files_for_this_format(self, context):
                """Retrieve .py files specifically for this export format."""
                return get_py_files(self, context, folder)

            # Create the property dynamically
            return bpy.props.EnumProperty(
                name=f"{export_format_key} Preset File",
                description=f"Select a preset file for {export_format_key}",
                items=lambda self, context: get_py_files_for_this_format(self, context),
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
    prefs = bpy.context.preferences.addons[base_package].preferences

    bpy.types.Scene.export_format = bpy.props.EnumProperty(
        name="Export Format",
        description="Select the export format",
        items=get_export_format_items(),  # Dynamically generated items from EXPORT_FORMATS
        default=get_default_export_format(),
        update=update_preset_path,  # Update the preset path when export format changes
    )

    bpy.types.Scene.override_path = bpy.props.BoolProperty(
        name="Overwrite Preset Folder",
        description="Manually override the automatically set preset folder",
        default=False,
    )

    bpy.types.Scene.custom_prefix = bpy.props.StringProperty(
        name=PROPERTY_METADATA["custom_prefix"]["name"],
        description=PROPERTY_METADATA["custom_prefix"]["description"],
        default=prefs.custom_prefix
    )
    bpy.types.Scene.custom_suffix = bpy.props.StringProperty(
        name=PROPERTY_METADATA["custom_suffix"]["name"],
        description=PROPERTY_METADATA["custom_suffix"]["description"],
        default=prefs.custom_suffix
    )
    bpy.types.Scene.use_blend_file_name_as_prefix = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["use_blend_file_name_as_prefix"]["name"],
        description=PROPERTY_METADATA["use_blend_file_name_as_prefix"]["description"],
        default=prefs.use_blend_file_name_as_prefix
    )
    bpy.types.Scene.set_location_offset_on_creation = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["set_location_offset_on_creation"]["name"],
        description=PROPERTY_METADATA["set_location_offset_on_creation"]["description"],
        default=prefs.set_location_offset_on_creation
    )
    bpy.types.Scene.move_by_collection_offset = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["move_by_collection_offset"]["name"],
        description=PROPERTY_METADATA["move_by_collection_offset"]["description"],
        default=prefs.move_by_collection_offset,
    )

    bpy.types.Scene.auto_set_filepath = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["auto_set_filepath"]["name"],
        description=PROPERTY_METADATA["auto_set_filepath"]["description"],
        default=prefs.auto_set_filepath
    )
    bpy.types.Scene.auto_set_preset = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["auto_set_preset"]["name"],
        description=PROPERTY_METADATA["auto_set_preset"]["description"],
        default=prefs.auto_set_preset
    )
    bpy.types.Scene.collection_color = bpy.props.EnumProperty(
        name=PROPERTY_METADATA["collection_color"]["name"],
        description=PROPERTY_METADATA["collection_color"]["description"],
        items=PROPERTY_METADATA["collection_color"]["items"],
        default=prefs.collection_color
    )


def initialize_properties_file_path():
    prefs = bpy.context.preferences.addons[base_package].preferences

    bpy.types.Scene.mirror_search_path = bpy.props.StringProperty(
        name=PROPERTY_METADATA["mirror_search_path"]["name"],
        description=PROPERTY_METADATA["mirror_search_path"]["description"],
        default=prefs.mirror_search_path,
        update=update_mirror_preview
    )
    bpy.types.Scene.mirror_replacement_path = bpy.props.StringProperty(
        name=PROPERTY_METADATA["mirror_replacement_path"]["name"],
        description=PROPERTY_METADATA["mirror_replacement_path"]["description"],
        default=prefs.mirror_replacement_path,
        update=update_mirror_preview
    )
    bpy.types.Scene.export_folder_mode = bpy.props.EnumProperty(
        name=PROPERTY_METADATA["export_folder_mode"]["name"],
        items=PROPERTY_METADATA["export_folder_mode"]["items"],
        description=PROPERTY_METADATA["export_folder_mode"]["description"],
        default=prefs.export_folder_mode
    )

    bpy.types.Scene.absolute_export_path = bpy.props.StringProperty(
        name=PROPERTY_METADATA["absolute_export_path"]["name"],
        description=PROPERTY_METADATA["absolute_export_path"]["description"],
        subtype='DIR_PATH',
        default=prefs.absolute_export_path,
        get=get_absolute_path,  # Use shared absolute path getter
        set=set_absolute_path  # Use shared absolute path setter
    )

    bpy.types.Scene.relative_export_path = bpy.props.StringProperty(
        name=PROPERTY_METADATA["relative_export_path"]["name"],
        description=PROPERTY_METADATA["relative_export_path"]["description"],
        subtype='DIR_PATH',
        default=prefs.relative_export_path,
        get=get_relative_path,  # Use extracted getter
        set=set_relative_path  # Use extracted setter
    )


def post_register():
    initialize_properties_collection_generation()
    initialize_properties_file_path()


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    # Initialize correct property panel for the Simple Export Panel
    update_panel_category(None, bpy.context)

    bpy.types.Scene.collection_index = bpy.props.IntProperty(
        name="Collection Index",
        description="Index of the active collection in the list",
        default=0
    )

    bpy.types.Scene.overwrite_filepath_settings = bpy.props.BoolProperty(
        name="Scene: Filepath",
        description="Overwrite the settings regarding the generation of the export path defined in the Preferences",
        default=True)

    bpy.types.Scene.overwrite_collection_settings = bpy.props.BoolProperty(
        name="Scene: Export Collection",
        description="Overwrite the settings related to the creation of Export Collections defined in the Preferences",
        default=False)

    bpy.types.Scene.overwrite_preset_settings = bpy.props.BoolProperty(
        name="Scene: Preset",
        description="Overwrite the settings regarding the presets",
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

    ########################################
    # Presets
    bpy.types.Scene.simple_export_preset_file_fbx = bpy.props.EnumProperty(
        name="FBX Preset File",
        description="Select a preset file for FBX",
        items=lambda self, context: get_py_files_for_fbx(self, context),
        update=update_preset_path_for_fbx,
    )

    bpy.types.Scene.simple_export_preset_file_obj = bpy.props.EnumProperty(
        name="OBJ Preset File",
        description="Select a preset file for OBJ",
        items=lambda self, context: get_py_files_for_obj(self, context),
        update=update_preset_path_for_obj,
    )

    bpy.types.Scene.simple_export_preset_file_gltf = bpy.props.EnumProperty(
        name="glTF Preset File",
        description="Select a preset file for glTF",
        items=lambda self, context: get_py_files_for_gltf(self, context),
        update=update_preset_path_for_gltf,
    )

    bpy.types.Scene.simple_export_preset_file_usd = bpy.props.EnumProperty(
        name="USD Preset File",
        description="Select a preset file for USD",
        items=lambda self, context: get_py_files_for_usd(self, context),
        update=update_preset_path_for_usd,
    )

    bpy.types.Scene.simple_export_preset_file_abc = bpy.props.EnumProperty(
        name="Alembic Preset File",
        description="Select a preset file for Alembic",
        items=lambda self, context: get_py_files_for_abc(self, context),
        update=update_preset_path_for_abc,
    )

    bpy.types.Scene.simple_export_preset_file_ply = bpy.props.EnumProperty(
        name="PLY Preset File",
        description="Select a preset file for PLY",
        items=lambda self, context: get_py_files_for_ply(self, context),
        update=update_preset_path_for_ply,
    )

    bpy.types.Scene.simple_export_preset_file_stl = bpy.props.EnumProperty(
        name="STL Preset File",
        description="Select a preset file for STL",
        items=lambda self, context: get_py_files_for_stl(self, context),
        update=update_preset_path_for_stl,
    )

    bpy.app.timers.register(post_register, first_interval=0.5)
    initialize_format_specific_properties()


def unregister():
    # Remove dynamically created properties
    for export_format in ExportFormats.FORMATS.keys():
        prop_name = f"simple_export_preset_file_{export_format.lower()}"
        if hasattr(bpy.types.Scene, prop_name):
            delattr(bpy.types.Scene, prop_name)

    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    # Persistant settings
    del bpy.types.Scene.collection_index
    del bpy.types.Collection.simple_export_selected
    del bpy.types.Collection.offset_object

    del bpy.types.Scene.overwrite_filepath_settings
    del bpy.types.Scene.overwrite_collection_settings

    # Collection creation
    del bpy.types.Scene.custom_prefix
    del bpy.types.Scene.custom_suffix
    del bpy.types.Scene.use_blend_file_name_as_prefix
    del bpy.types.Scene.set_location_offset_on_creation
    del bpy.types.Scene.auto_set_filepath
    del bpy.types.Scene.auto_set_preset
    del bpy.types.Scene.collection_color

    # filepath
    del bpy.types.Scene.mirror_search_path
    del bpy.types.Scene.mirror_replacement_path
    del bpy.types.Scene.export_folder_mode
    del bpy.types.Scene.absolute_export_path
    del bpy.types.Scene.relative_export_path

    del bpy.types.Scene.simple_export_preset_file_fbx
    del bpy.types.Scene.simple_export_preset_file_obj
    del bpy.types.Scene.simple_export_preset_file_gltf
    del bpy.types.Scene.simple_export_preset_file_usd
    del bpy.types.Scene.simple_export_preset_file_abc
    del bpy.types.Scene.simple_export_preset_file_ply
    del bpy.types.Scene.simple_export_preset_file_stl
