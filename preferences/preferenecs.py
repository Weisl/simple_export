import os

import bpy

from .. import __package__ as base_package
from ..core.export_formats import ExportFormats
from ..core.export_formats import get_export_format_items
from ..ui.export_panels import VIEW3D_PT_SimpleExportMain, VIEW3D_PT_SimpleExportSettings

PROPERTY_METADATA = {

    # Collection Naming Props
    "collection_prefix": {
        "name": "Prefix",
        "description": "Custom prefix added to export collections.",
        "default": "",
    },
    "collection_suffix": {
        "name": "Suffix",
        "description": "Custom suffix added to the export collections.",
        "default": "",
    },

    "collection_blend_prefix": {
        "name": "Blend Name as Prefix",
        "description": "Add the blend file name as prefix to the export collections.",
        "default": False,
    },

    # File Path Settings

    "export_folder_mode": {
        "name": "Custom Export Path Mode",
        "description": "Choose how the export file path is determined",
        "default": "RELATIVE",
        "items": [
            ("ABSOLUTE", "Absolute", "Use an absolute file path"),
            ("RELATIVE", "Relative", "Use a file path relative to the .blend file"),
            ("MIRROR", "Mirror", "Mirror part of the blend file path with another directory"),
        ],
    },

    "folder_path_absolute": {
        "name": "Export Folder",
        "description": "Custom absolute folder to export files to.",
        "default": '',
    },

    "folder_path_relative": {
        "name": "Relative Folder Path",
        "description": "Folder to export files relative to the .blend file.",
        "default": '//.',
    },

    "folder_path_search": {
        "name": "Search",
        "description": "The path to be replaced.",
        "default": "workdata",
    },

    "folder_path_replace": {
        "name": "Replace",
        "description": "The path to replace with.",
        "default": "sourcedata",
    },

    # Filename Naming Props

    "filename_prefix": {
        "name": "Prefix",
        "description": "Custom prefix added when to the export filename.",
        "default": "",
    },
    "filename_suffix": {
        "name": "Suffix",
        "description": "Custom suffix added when to the export filename.",
        "default": "",
    },
    "filename_blend_prefix": {
        "name": "Blend Name Prefix",
        "description": "Add the blend file name as prefix to the export filename.",
        "default": False,
    },

    # Set Folder Path

    "set_export_path": {
        "name": "Assign Export Path",
        "description": "Set filepath when creating an Exporter Collection.",
        "default": True,
    },

    # Set Preset

    "assign_preset": {
        "name": "Assign Export Preset",
        "description": "Set export preset when creating an Exporter Collection.",
        "default": True,
    },

    "parent_collection": {
        "name": "Parent Collection",
        "description": "Specify the Name of the Parent Collection. Ignored if empty",
        "default": ''},

    # collection Settings

    # Collection Color
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

    "collection_instance_offset": {
        "name": "Set Collection Center Location",
        "description": "Use active object as Collection Instance Offset.",
        "default": False,
    },

    "use_root_object": {
        "name": "Assign Root Object",
        "description": "Use active object as Collection Instance Offset and link it.",
        "default": True,
    },
    "move_by_collection_offset": {
        "name": "Move Collection to Origin",
        "description": "Objects are moved to the origin based on the Collection Center or root object before exporting.",
        "default": False,
    },
}


def setdefaultpreset():
    # Replicate the logic of get_simple_export_preset_files to get the list of files
    preset_folder = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets", "simple_export")
    # Create the folder if it doesn't exist
    os.makedirs(preset_folder, exist_ok=True)
    # Check if the user has specified a custom preset folder
    py_files = [f for f in os.listdir(preset_folder) if f.endswith('.py')]
    try:
        return py_files.index('UE-default.py')
    except ValueError:
        return 0  # Fallback to first item if not found


def get_simple_export_preset_files(self, context):
    """Get a list of available preset files for simple export."""
    preset_folder = os.path.join(bpy.utils.user_resource('SCRIPTS'), "presets", "simple_export")

    # Check if the user has specified a custom preset folder
    prefs = context.preferences.addons[base_package].preferences
    if prefs.preset_path_override and os.path.isdir(bpy.path.abspath(prefs.preset_path_override)):
        preset_folder = bpy.path.abspath(prefs.preset_path_override)

    return get_py_files(self, context, preset_folder)


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


def update_panel_category(self, context):
    """Update panel tab for simple export"""
    panels = [
        VIEW3D_PT_SimpleExportMain,
        VIEW3D_PT_SimpleExportSettings,
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
    if not settings.folder_path_search or not settings.folder_path_replace:
        return "Invalid search/replacement paths"

    # Ensure blend file path contains the search path before replacing
    if settings.folder_path_search in blend_path:
        export_path = blend_path.replace(settings.folder_path_search, settings.folder_path_replace)
        return bpy.path.relpath(export_path) if "//" in export_path else export_path

    return "Search Path not found in current blend file path"


def get_relative_path(instance):
    """Ensure the stored path is always relative to the .blend file."""
    if isinstance(instance, bpy.types.AddonPreferences):
        # If called from AddonPreferences
        stored_path = instance.get("folder_path_relative", "")
    elif isinstance(instance, bpy.types.Scene):
        # If called from Scene (fallback)
        stored_path = instance.get("folder_path_relative", "")
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
            instance["folder_path_relative"] = value  # Store as-is
        elif isinstance(instance, bpy.types.Scene):
            instance["folder_path_relative"] = value  # Store in scene
        return

    absolute_path = bpy.path.abspath(value)  # Convert input to absolute path

    try:
        # Use `os.path.relpath()` to ensure a clean direct relative path
        relative_path = os.path.relpath(absolute_path, blend_dir)
        formatted_path = f"//{relative_path.replace(os.sep, '/')}"

        if isinstance(instance, bpy.types.AddonPreferences):
            instance["folder_path_relative"] = formatted_path
        elif isinstance(instance, bpy.types.Scene):
            instance["folder_path_relative"] = formatted_path
    except ValueError:
        # Path is outside the blend directory, reset to empty
        if isinstance(instance, bpy.types.AddonPreferences):
            instance["folder_path_relative"] = ""
        elif isinstance(instance, bpy.types.Scene):
            instance["folder_path_relative"] = ""


def get_absolute_path(instance):
    """Ensure the stored path is always an absolute path."""
    if isinstance(instance, bpy.types.AddonPreferences):
        # If called from AddonPreferences
        stored_path = instance.get("folder_path_absolute", "")
    elif isinstance(instance, bpy.types.Scene):
        # If called from Scene (fallback)
        stored_path = instance.get("folder_path_absolute", "")
    else:
        return ""

    if stored_path:
        return bpy.path.abspath(stored_path)  # Convert to absolute path
    return ""


def set_absolute_path(instance, value):
    """Convert any assigned path to an absolute path."""
    absolute_path = bpy.path.abspath(value)  # Ensure absolute path format

    if isinstance(instance, bpy.types.AddonPreferences):
        instance["folder_path_absolute"] = absolute_path
    elif isinstance(instance, bpy.types.Scene):
        instance["folder_path_absolute"] = absolute_path


class SIMPLE_EXPORT_preferences(bpy.types.AddonPreferences):
    bl_idname = base_package
    bl_options = {'REGISTER'}

    def update_simple_export_panel_key(self, context):
        wm = context.window_manager
        addon_km = wm.keyconfigs.addon.keymaps.get("Window")
        if not addon_km:
            return

        # Remove existing keymap items for this addon
        for kmi in addon_km.keymap_items[:]:
            if kmi.idname == 'wm.call_panel' and hasattr(kmi.properties,
                                                         'name') and kmi.properties.name == "SIMPLE_EXPORT_PT_simple_export_popup":
                addon_km.keymap_items.remove(kmi)

        # Add new keymap items
        simple_export_panel_type = self.simple_export_panel_type.upper()
        if simple_export_panel_type != 'NONE':
            kmi = addon_km.keymap_items.new(
                idname='wm.call_panel',
                type=simple_export_panel_type,
                value='PRESS',
                ctrl=self.simple_export_panel_ctrl,
                shift=self.simple_export_panel_shift,
                alt=self.simple_export_panel_alt,
            )
            kmi.properties.name = "SIMPLE_EXPORT_PT_simple_export_popup"
            kmi.active = self.simple_export_panel_active

    # Preference UI properties
    prefs_tabs: bpy.props.EnumProperty(
        name='Export Preferences',
        items=(('SETTINGS', "Defaults", "General addon presets"),
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

    ########################################
    # Filepath
    export_folder_mode: bpy.props.EnumProperty(
        name=PROPERTY_METADATA["export_folder_mode"]["name"],
        description=PROPERTY_METADATA["export_folder_mode"]["description"],
        items=PROPERTY_METADATA["export_folder_mode"]["items"],
        default=PROPERTY_METADATA["export_folder_mode"]["default"],
    )

    folder_path_absolute: bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_absolute"]["name"],
        description=PROPERTY_METADATA["folder_path_absolute"]["description"],
        default=PROPERTY_METADATA["folder_path_absolute"]["default"],
        subtype='DIR_PATH',
        get=get_absolute_path,  # Use shared absolute path getter
        set=set_absolute_path  # Use shared absolute path setter
    )

    folder_path_relative: bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_relative"]["name"],
        description=PROPERTY_METADATA["folder_path_relative"]["description"],
        default=PROPERTY_METADATA["folder_path_relative"]["default"],
        get=get_relative_path,  # Use the same getter
        set=set_relative_path  # Use the same setter
    )

    folder_path_search: bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_search"]["name"],
        description=PROPERTY_METADATA["folder_path_search"]["description"],
        default=PROPERTY_METADATA["folder_path_search"]["default"],
        update=update_mirror_preview,
    )

    folder_path_replace: bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_replace"]["name"],
        description=PROPERTY_METADATA["folder_path_replace"]["description"],
        default=PROPERTY_METADATA["folder_path_replace"]["default"],
        update=update_mirror_preview,
    )

    ########################################
    # Filename

    filename_prefix: bpy.props.StringProperty(
        name=PROPERTY_METADATA["filename_prefix"]["name"],
        description=PROPERTY_METADATA["filename_prefix"]["description"],
        default=PROPERTY_METADATA["filename_prefix"]["default"],
    )

    filename_suffix: bpy.props.StringProperty(
        name=PROPERTY_METADATA["filename_suffix"]["name"],
        description=PROPERTY_METADATA["filename_suffix"]["description"],
        default=PROPERTY_METADATA["filename_suffix"]["default"],
    )

    filename_blend_prefix: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["filename_blend_prefix"]["name"],
        description=PROPERTY_METADATA["filename_blend_prefix"]["description"],
        default=PROPERTY_METADATA["filename_blend_prefix"]["default"],
    )

    ########################################
    # Collection Name

    collection_prefix: bpy.props.StringProperty(
        name=PROPERTY_METADATA["collection_prefix"]["name"],
        description=PROPERTY_METADATA["collection_prefix"]["description"],
        default=PROPERTY_METADATA["collection_prefix"]["default"],
    )

    collection_suffix: bpy.props.StringProperty(
        name=PROPERTY_METADATA["collection_suffix"]["name"],
        description=PROPERTY_METADATA["collection_suffix"]["description"],
        default=PROPERTY_METADATA["collection_suffix"]["default"],
    )

    collection_blend_prefix: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["collection_blend_prefix"]["name"],
        description=PROPERTY_METADATA["collection_blend_prefix"]["description"],
        default=PROPERTY_METADATA["collection_blend_prefix"]["default"],
    )

    ########################################
    # Collections Settings

    collection_instance_offset: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["collection_instance_offset"]["name"],
        description=PROPERTY_METADATA["collection_instance_offset"]["description"],
        default=PROPERTY_METADATA["collection_instance_offset"]["default"],
    )

    use_root_object: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["use_root_object"]["name"],
        description=PROPERTY_METADATA["use_root_object"]["description"],
        default=PROPERTY_METADATA["use_root_object"]["default"],
    )

    collection_color: bpy.props.EnumProperty(
        name=PROPERTY_METADATA["collection_color"]["name"],
        description=PROPERTY_METADATA["collection_color"]["description"],
        items=PROPERTY_METADATA["collection_color"]["items"],
        default=PROPERTY_METADATA["collection_color"]["default"],
    )

    set_export_path: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["set_export_path"]["name"],
        description=PROPERTY_METADATA["set_export_path"]["description"],
        default=PROPERTY_METADATA["set_export_path"]["default"],
    )

    assign_preset: bpy.props.BoolProperty(
        name=PROPERTY_METADATA["assign_preset"]["name"],
        description=PROPERTY_METADATA["assign_preset"]["description"],
        default=PROPERTY_METADATA["assign_preset"]["default"],
    )

    parent_collection: bpy.props.StringProperty(
        name=PROPERTY_METADATA["parent_collection"]["name"],
        description=PROPERTY_METADATA["parent_collection"]["description"],
        default=PROPERTY_METADATA["parent_collection"]["default"],
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

    panel_category: bpy.props.StringProperty(name="Category Tab",
                                             description="The category name used to organize the addon in the properties panel for all the addons",
                                             default='Simple Export',
                                             update=update_panel_category)  # update = update_panel_position,

    enable_n_panel: bpy.props.BoolProperty(
        name="Enable Simple Export N-Panel",
        description="Toggle the N-Panel on and off.",
        default=True,
        update=update_panel_category)

    ########################################
    # Presets

    simple_export_default_preset: bpy.props.EnumProperty(
        name="Simple Default Preset",
        description="Select a default preset",
        items=lambda self, context: get_simple_export_preset_files(self, context),
        default=setdefaultpreset()
    )

    ########################################

    preset_path_override: bpy.props.StringProperty(
        name="Overwrite Preset Folder",
        description="Override the default Blender preset folder",
        subtype='DIR_PATH',
    )

    simple_export_preset_file_fbx: bpy.props.EnumProperty(
        name="FBX Preset File",
        description="Select a preset file for FBX",
        items=lambda self, context: get_py_files_for_fbx(self, context),
    )

    simple_export_preset_file_obj: bpy.props.EnumProperty(
        name="OBJ Preset File",
        description="Select a preset file for OBJ",
        items=lambda self, context: get_py_files_for_obj(self, context),
    )

    simple_export_preset_file_gltf: bpy.props.EnumProperty(
        name="glTF Preset File",
        description="Select a preset file for glTF",
        items=lambda self, context: get_py_files_for_gltf(self, context),
    )
    simple_export_preset_file_usd: bpy.props.EnumProperty(
        name="USD Preset File",
        description="Select a preset file for USD",
        items=lambda self, context: get_py_files_for_usd(self, context),
    )

    simple_export_preset_file_abc: bpy.props.EnumProperty(
        name="Alembic Preset File",
        description="Select a preset file for Alembic",
        items=lambda self, context: get_py_files_for_abc(self, context),
    )

    simple_export_preset_file_ply: bpy.props.EnumProperty(
        name="PLY Preset File",
        description="Select a preset file for PLY",
        items=lambda self, context: get_py_files_for_ply(self, context),
    )

    simple_export_preset_file_stl: bpy.props.EnumProperty(
        name="STL Preset File",
        description="Select a preset file for STL",
        items=lambda self, context: get_py_files_for_stl(self, context),
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
            box = layout.box()

            row = box.row(align=True)

            row.label(text="Default Export Preset")
            row.prop(self, "simple_export_default_preset", text="")

            # Operator to open a folder
            folder_op = row.operator("file.external_operation", text='', icon='FILE_FOLDER')
            folder_op.operation = 'FOLDER_OPEN'
            from ..presets_addon.exporter_preset import simple_export_presets_folder
            folder_op.filepath = simple_export_presets_folder()

        elif self.prefs_tabs == 'UI':

            box = layout.box()
            box.label(text="N Panel")
            box.prop(self, 'enable_n_panel')
            box.prop(self, 'panel_category')

            box = layout.box()
            box.label(text="Warnings")
            box.prop(self, "report_errors_only")


        elif self.prefs_tabs == 'KEYMAP':
            self.keymap_ui(layout, 'Export Popup', 'simple_export_panel', 'wm.call_panel',
                           "SIMPLE_EXPORT_PT_simple_export_popup")


# Initialize Window Manager Properties with Add-on Preferences Defaults

classes = (
    SIMPLE_EXPORT_preferences,
)


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
            preset_path = bpy.context.preferences.addons[base_package].preferences.preset_path

        folder = preset_path

    if not folder or not os.path.isdir(folder):
        # print(f"[DEBUG] Invalid folder: {folder}")
        return [("NONE", "Create Presets",
                 "Create export presets export in Blender's default export window before assigning them in Simple Export.")]

    try:
        files = [
            (os.path.join(folder, f), f, "")
            for f in os.listdir(folder)
            if f.endswith(".py")
        ]
        # print(f"[DEBUG] Files found in {folder}: {files}")
        return files if files else [
            ("NONE", "No Files", "Create presets export in the default export windows before assigning them.")]
    except Exception as e:
        # print(f"[DEBUG ERROR] Error reading files in {folder}: {e}")
        return [("NONE", "Error", str(e))]


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
        default=prefs.default_export_format,
    )

    bpy.types.Scene.override_path = bpy.props.BoolProperty(
        name="Overwrite Preset Folder",
        description="Manually override the automatically set preset folder",
        default=False,
    )

    # collection Naming
    bpy.types.Scene.collection_prefix = bpy.props.StringProperty(
        name=PROPERTY_METADATA["collection_prefix"]["name"],
        description=PROPERTY_METADATA["collection_prefix"]["description"],
        default=prefs.collection_prefix
    )
    bpy.types.Scene.collection_suffix = bpy.props.StringProperty(
        name=PROPERTY_METADATA["collection_suffix"]["name"],
        description=PROPERTY_METADATA["collection_suffix"]["description"],
        default=prefs.collection_suffix
    )
    bpy.types.Scene.collection_blend_prefix = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["collection_blend_prefix"]["name"],
        description=PROPERTY_METADATA["collection_blend_prefix"]["description"],
        default=prefs.collection_blend_prefix
    )

    # filename settings
    bpy.types.Scene.filename_prefix = bpy.props.StringProperty(
        name=PROPERTY_METADATA["filename_prefix"]["name"],
        description=PROPERTY_METADATA["filename_prefix"]["description"],
        default=prefs.filename_prefix
    )
    bpy.types.Scene.filename_suffix = bpy.props.StringProperty(
        name=PROPERTY_METADATA["filename_suffix"]["name"],
        description=PROPERTY_METADATA["filename_suffix"]["description"],
        default=prefs.filename_suffix
    )
    bpy.types.Scene.filename_blend_prefix = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["filename_blend_prefix"]["name"],
        description=PROPERTY_METADATA["filename_blend_prefix"]["description"],
        default=prefs.filename_blend_prefix
    )

    # Collection creation settings
    bpy.types.Scene.collection_instance_offset = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["collection_instance_offset"]["name"],
        description=PROPERTY_METADATA["collection_instance_offset"]["description"],
        default=prefs.collection_instance_offset
    )

    bpy.types.Scene.use_root_object = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["use_root_object"]["name"],
        description=PROPERTY_METADATA["use_root_object"]["description"],
        default=prefs.use_root_object
    )

    bpy.types.Scene.set_export_path = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["set_export_path"]["name"],
        description=PROPERTY_METADATA["set_export_path"]["description"],
        default=prefs.set_export_path
    )
    bpy.types.Scene.assign_preset = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["assign_preset"]["name"],
        description=PROPERTY_METADATA["assign_preset"]["description"],
        default=prefs.assign_preset
    )

    bpy.types.Scene.parent_collection = bpy.props.StringProperty(
        name=PROPERTY_METADATA["parent_collection"]["name"],
        description=PROPERTY_METADATA["parent_collection"]["description"],
        default=PROPERTY_METADATA["parent_collection"]["default"],
    )

    bpy.types.Scene.collection_color = bpy.props.EnumProperty(
        name=PROPERTY_METADATA["collection_color"]["name"],
        description=PROPERTY_METADATA["collection_color"]["description"],
        items=PROPERTY_METADATA["collection_color"]["items"],
        default=prefs.collection_color
    )

    # Pre Export operations
    bpy.types.Scene.move_by_collection_offset = bpy.props.BoolProperty(
        name=PROPERTY_METADATA["move_by_collection_offset"]["name"],
        description=PROPERTY_METADATA["move_by_collection_offset"]["description"],
        default=prefs.move_by_collection_offset,
    )


def initialize_properties_file_path():
    prefs = bpy.context.preferences.addons[base_package].preferences

    bpy.types.Scene.folder_path_search = bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_search"]["name"],
        description=PROPERTY_METADATA["folder_path_search"]["description"],
        default=prefs.folder_path_search,
        update=update_mirror_preview
    )
    bpy.types.Scene.folder_path_replace = bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_replace"]["name"],
        description=PROPERTY_METADATA["folder_path_replace"]["description"],
        default=prefs.folder_path_replace,
        update=update_mirror_preview
    )
    bpy.types.Scene.export_folder_mode = bpy.props.EnumProperty(
        name=PROPERTY_METADATA["export_folder_mode"]["name"],
        items=PROPERTY_METADATA["export_folder_mode"]["items"],
        description=PROPERTY_METADATA["export_folder_mode"]["description"],
        default=prefs.export_folder_mode
    )

    bpy.types.Scene.folder_path_absolute = bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_absolute"]["name"],
        description=PROPERTY_METADATA["folder_path_absolute"]["description"],
        subtype='DIR_PATH',
        default=prefs.folder_path_absolute,
        get=get_absolute_path,  # Use shared absolute path getter
        set=set_absolute_path  # Use shared absolute path setter
    )

    bpy.types.Scene.folder_path_relative = bpy.props.StringProperty(
        name=PROPERTY_METADATA["folder_path_relative"]["name"],
        description=PROPERTY_METADATA["folder_path_relative"]["description"],
        default=prefs.folder_path_relative,
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

    ########################################
    # Presets
    bpy.types.Scene.simple_export_preset_file_fbx = bpy.props.EnumProperty(
        name="FBX Preset File",
        description="Select a preset file for FBX",
        items=lambda self, context: get_py_files_for_fbx(self, context),
    )

    bpy.types.Scene.simple_export_preset_file_obj = bpy.props.EnumProperty(
        name="OBJ Preset File",
        description="Select a preset file for OBJ",
        items=lambda self, context: get_py_files_for_obj(self, context),
    )

    bpy.types.Scene.simple_export_preset_file_gltf = bpy.props.EnumProperty(
        name="glTF Preset File",
        description="Select a preset file for glTF",
        items=lambda self, context: get_py_files_for_gltf(self, context),
    )

    bpy.types.Scene.simple_export_preset_file_usd = bpy.props.EnumProperty(
        name="USD Preset File",
        description="Select a preset file for USD",
        items=lambda self, context: get_py_files_for_usd(self, context),
    )

    bpy.types.Scene.simple_export_preset_file_abc = bpy.props.EnumProperty(
        name="Alembic Preset File",
        description="Select a preset file for Alembic",
        items=lambda self, context: get_py_files_for_abc(self, context),
    )

    bpy.types.Scene.simple_export_preset_file_ply = bpy.props.EnumProperty(
        name="PLY Preset File",
        description="Select a preset file for PLY",
        items=lambda self, context: get_py_files_for_ply(self, context),
    )

    bpy.types.Scene.simple_export_preset_file_stl = bpy.props.EnumProperty(
        name="STL Preset File",
        description="Select a preset file for STL",
        items=lambda self, context: get_py_files_for_stl(self, context),
    )

    bpy.app.timers.register(post_register, first_interval=0.5)
    initialize_format_specific_properties()
    initialize_properties_collection_generation()
    initialize_properties_file_path()


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

    # Export format
    del bpy.types.Scene.export_format
    del bpy.types.Scene.override_path

    # Collection creation
    del bpy.types.Scene.collection_prefix
    del bpy.types.Scene.collection_suffix
    del bpy.types.Scene.collection_blend_prefix
    del bpy.types.Scene.filename_blend_prefix
    del bpy.types.Scene.filename_prefix
    del bpy.types.Scene.filename_suffix
    del bpy.types.Scene.collection_instance_offset
    del bpy.types.Scene.use_root_object
    del bpy.types.Scene.set_export_path
    del bpy.types.Scene.assign_preset
    del bpy.types.Scene.parent_collection
    del bpy.types.Scene.collection_color

    # filepath
    del bpy.types.Scene.folder_path_search
    del bpy.types.Scene.folder_path_replace
    del bpy.types.Scene.export_folder_mode
    del bpy.types.Scene.folder_path_absolute
    del bpy.types.Scene.folder_path_relative

    # Pre export operations
    del bpy.types.Scene.move_by_collection_offset
