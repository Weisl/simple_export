import bpy
import os

from .. import __package__ as base_package
from ..core.info import ADDON_NAME, COLOR_TAG_ICONS
from ..functions.exporter_funcs import find_exporter


def draw_pre_export_operations(col, scene):
    # Ensure the panel is collapsed by default
    header, body = col.panel(idname="PRE_EXPORT_OPERATIONS_PANEL", default_closed=True)

    icon = 'WARNING_LARGE' if bpy.app.version >= (4, 3, 0) else 'ERROR'

    # Draw the panel header
    header.label(text="Pre Export Operations (BETA)", icon=icon)

    # Check if the panel is expanded before drawing elements
    if body:
        body.prop(scene, 'move_by_collection_offset')


def draw_simple_export_header(layout):
    row = layout.row(align=True)
    # Open documentation
    row.operator("wm.url_open", text="", icon="HELP").url = "https://weisl.github.io/exporter_overview/"
    # Open Preferences
    addon_name = ADDON_NAME
    op = row.operator("simple_export.open_preferences", text="", icon="PREFERENCES")
    op.addon_name = addon_name
    op.prefs_tabs = 'SETTINGS'
    # Open Export Popup
    op = row.operator("wm.call_panel", text="", icon="WINDOW")
    op.name = "SIMPLE_EXPORT_PT_simple_export_popup"
    row.label(text="Simple Export")


def get_operator_properties(context):
    """Gather operator properties from preferences and scene settings."""
    prefs = context.preferences.addons[base_package].preferences
    scene = context.scene

    # Determine which settings to use (scene overwrites preferences)
    settings_col = scene if scene.overwrite_collection_settings else prefs

    # Get naming properties
    prefix = getattr(settings_col, 'collection_prefix', '')
    suffix = getattr(settings_col, 'collection_suffix', '')
    file_name_prefix = getattr(settings_col, 'filename_blend_prefix', False)

    # Get collection properties
    collection_color = getattr(settings_col, 'collection_color', 'NONE')
    collection_instance_offset = getattr(settings_col, 'collection_set_location_offset_on_creation', False)
    use_root_object = getattr(settings_col, 'collection_use_root_offset_object', True)

    # Get preset and filepath properties
    overwrite_preset = getattr(settings_col, 'set_preset', False)
    overwrite_filepath = getattr(settings_col, 'set_export_path', False)

    # set_preset and set_export_path follow the same logic
    set_preset = overwrite_preset
    set_export_path = overwrite_filepath

    # Get preset filepath if auto-set is enabled
    preset_filepath = ""
    if overwrite_preset:
        export_format = scene.export_format.lower()
        prop_name = f"simple_export_preset_file_{export_format}"
        preset_settings = scene if scene.overwrite_preset_settings else prefs
        preset_filepath = getattr(preset_settings, prop_name, "")

    # Get export filepath if auto-set is enabled
    if overwrite_filepath:
        # This would need to be calculated based on the collection and export settings
        # For now, we'll leave it empty and let the operator handle it
        pass

    return {
        'collection_prefix': prefix,
        'collection_suffix': suffix,
        'filename_blend_prefix': file_name_prefix,
        'collection_color': collection_color,
        'collection_instance_offset': collection_instance_offset,
        'use_root_object': use_root_object,
        'preset_filepath': preset_filepath,
        'set_preset': set_preset,
        'set_export_path': set_export_path,
    }


def get_filename_properties(context):
    """Gather filename properties from preferences and scene settings."""
    prefs = context.preferences.addons[base_package].preferences
    scene = context.scene

    # Determine which settings to use (scene overwrites preferences)
    settings_filename = scene if scene.overwrite_filename_settings else prefs

    # Get filename properties
    filename_prefix = getattr(settings_filename, 'filename_prefix', '')
    filename_suffix = getattr(settings_filename, 'filename_suffix', '')
    filename_blend_prefix = getattr(settings_filename, 'filename_blend_prefix', False)

    return {
        'filename_prefix': filename_prefix,
        'filename_suffix': filename_suffix,
        'filename_blend_prefix': filename_blend_prefix,
    }


def get_filepath_properties(context):
    """Gather filepath properties from preferences and scene settings."""
    prefs = context.preferences.addons[base_package].preferences
    scene = context.scene

    # Determine which settings to use (scene overwrites preferences)
    settings_filepath = scene if scene.overwrite_filepath_settings else prefs

    # Get filepath properties
    export_folder_mode = getattr(settings_filepath, 'export_folder_mode', 'RELATIVE')
    folder_path_absolute = getattr(settings_filepath, 'folder_path_absolute', '')
    folder_path_relative = getattr(settings_filepath, 'folder_path_relative', '')
    folder_path_search = getattr(settings_filepath, 'folder_path_search', '')
    folder_path_replace = getattr(settings_filepath, 'folder_path_replace', '')

    return {
        'export_folder_mode': export_folder_mode,
        'folder_path_absolute': folder_path_absolute,
        'folder_path_relative': folder_path_relative,
        'folder_path_search': folder_path_search,
        'folder_path_replace': folder_path_replace,
    }


def get_set_export_paths_properties(context):
    """Gather all properties needed for the set_export_paths operator and export folder UI."""
    filepath_props = get_filepath_properties(context)
    filename_props = get_filename_properties(context)
    # Combine all properties
    all_props = {}
    all_props.update(filepath_props)
    all_props.update(filename_props)
    # Explicitly include export folder settings for clarity
    all_props['export_folder_mode'] = filepath_props['export_folder_mode']
    all_props['folder_path_absolute'] = filepath_props['folder_path_absolute']
    all_props['folder_path_relative'] = filepath_props['folder_path_relative']
    all_props['folder_path_search'] = filepath_props['folder_path_search']
    all_props['folder_path_replace'] = filepath_props['folder_path_replace']
    return all_props


def draw_collection_creation(context, layout):
    # Parent selection
    row = layout.row()
    color_tag = None
    if context.scene.parent_collection:
        color_tag = context.scene.parent_collection.color_tag
    icon = COLOR_TAG_ICONS.get(color_tag, 'OUTLINER_COLLECTION')
    row.prop(context.scene, "parent_collection", text="Parent Collection", icon=icon)
    # Draw Create Button
    row = layout.row()
    prefs = context.preferences.addons[base_package].preferences
    color_tag = prefs.collection_color
    icon = COLOR_TAG_ICONS.get(color_tag, 'OUTLINER_COLLECTION')
    op = row.operator("simple_export.create_export_collections", icon=icon)

    # Set default properties
    op.only_selection = True
    op.collection_naming_overwrite = False
    op.collection_name_new = ""
    op.use_numbering = False
    op.parent_collection_name = context.scene.parent_collection.name if context.scene.parent_collection else ""

    # Get and set properties from preferences/scene
    props = get_operator_properties(context)
    path_props = get_set_export_paths_properties(context)
    op.collection_prefix = props['collection_prefix']
    op.collection_suffix = props['collection_suffix']
    op.filename_blend_prefix = props['filename_blend_prefix']
    op.collection_color = props['collection_color']
    op.collection_instance_offset = props['collection_instance_offset']
    op.use_root_object = props['use_root_object']
    op.preset_filepath = props['preset_filepath']
    op.set_preset = props['set_preset']
    op.set_export_path = props['set_export_path']
    op.export_folder_mode = path_props['export_folder_mode']
    op.folder_path_absolute = path_props['folder_path_absolute']
    op.folder_path_relative = path_props['folder_path_relative']
    op.folder_path_search = path_props['folder_path_search']
    op.folder_path_replace = path_props['folder_path_replace']
    op.filename_prefix = path_props['filename_prefix']
    op.filename_suffix = path_props['filename_suffix']
    op.filename_blend_prefix = path_props['filename_blend_prefix']


def draw_scene_settings_overwrite(context, layout, scene):
    # Collapsible Filepath Settings Section
    header, body = layout.panel("overwrite_settings", default_closed=False)
    # Header
    addon_name = ADDON_NAME
    row = header.row(align=True)
    row.label(text='Exporter Settings (Scene)')
    op = row.operator("simple_export.open_preferences", text="", icon="PREFERENCES")
    op.addon_name = addon_name
    op.prefs_tabs = 'SETTINGS'
    # Body
    if body:
        row = body.row()
        row.prop(scene, 'overwrite_filepath_settings')
        box = body.box()
        draw_filepath_settings(box, context)

        row = body.row()
        row.prop(scene, 'overwrite_filename_settings')
        box = body.box()
        draw_name_settings(box, context)

        row = body.row()
        row.prop(scene, 'overwrite_preset_settings')
        box = body.box()
        draw_preset_settings(box, context)

        row = body.row()
        row.prop(scene, 'overwrite_collection_settings')

        box = body.box()
        draw_create_export_collections(box, context)


def draw_active_list_element(layout, scene):
    # Ensure valid selection before showing details
    if 0 <= scene.collection_index < len(bpy.data.collections):
        selected_collection = bpy.data.collections[scene.collection_index]

        # Draw the panel header
        header, body = layout.panel(idname="ACTIVE_COL_PANEL", default_closed=True)
        header.label(text=f"Active Collection:", icon='OUTLINER_COLLECTION')

        if body:
            # Export Path
            exporter = find_exporter(selected_collection, scene.export_format)

            # Return early
            if not exporter:
                layout.label(text='Select Collection', icon='INFO')
                return

            box = layout.box()
            # Collection name and icon
            row = box.row(align=True)

            row.prop(selected_collection, 'name', icon='OUTLINER_COLLECTION')
            op = row.operator("simple_export.open_exporter_in_properties", text="",
                              icon='PROPERTIES')
            op.collection_name = selected_collection.name

            row = box.row(align=True)
            row.prop(exporter.export_properties, "filepath", text="", expand=True)
            op = row.operator("simple_export.set_export_paths", text="", icon='FOLDER_REDIRECT')
            op.outliner = False
            op.individual_collection = True
            op.collection_name = selected_collection.name

            # Get and set all properties
            props = get_set_export_paths_properties(context)

            # Set all properties
            op.export_folder_mode = props['export_folder_mode']
            op.folder_path_absolute = props['folder_path_absolute']
            op.folder_path_relative = props['folder_path_relative']
            op.folder_path_search = props['folder_path_search']
            op.folder_path_replace = props['folder_path_replace']
            op.filename_prefix = props['filename_prefix']
            op.filename_suffix = props['filename_suffix']
            op.filename_blend_prefix = props['filename_blend_prefix']

            # Collection Center

            row = box.row(align=True)
            row.label(text='Root Object')

            row = box.row(align=True)

            box.prop(selected_collection, "use_root_object", text="Use Root Object")

            # No valid root object
            if not selected_collection.use_root_object:
                root_box = box.box()
                row = root_box.row(align=True)
                # Draw existing instancing properties
                row.prop(selected_collection, "instance_offset", text='Collection Center')

                col = root_box.column(align=True)
                # Add an operator button to manually update the offset if needed
                op = col.operator("object.set_collection_offset_cursor", text="Set Offset from Cursor")
                op.collection_name = selected_collection.name
                op = col.operator("object.set_collection_offset_object", text="Set Offset from Object")
                op.collection_name = selected_collection.name

            # Add the Object Picker
            else:
                box.prop(selected_collection, "root_object", text="Root Object")
                root_box = box.box()

                if selected_collection["root_object"]:
                    root_box.enabled = False
                    row = root_box.row(align=True)
                    # Draw existing instancing properties
                    row.prop(selected_collection, "instance_offset", text='Collection Center')
                else:
                    row = root_box.row(align=True)
                    # Draw existing instancing properties
                    row.prop(selected_collection, "instance_offset", text='Collection Center')

                    col = root_box.column(align=True)
                    # Add an operator button to manually update the offset if needed
                    op = col.operator("object.set_collection_offset_cursor", text="Set Offset from Cursor")
                    op.collection_name = selected_collection.name
                    op = col.operator("object.set_collection_offset_object", text="Set Offset from Object")
                    op.collection_name = selected_collection.name


def draw_export_list(layout, list_id, scene):
    # Export List
    row = layout.row()
    row.label(text="Export List")
    row = layout.row(align=True)
    op = row.operator("scene.select_all_collections", text="All", icon="CHECKBOX_HLT")
    op.deselect = False
    op = row.operator("scene.select_all_collections", text="None", icon="CHECKBOX_DEHLT")
    op.deselect = True
    # Display export list
    layout.template_list("SCENE_UL_CollectionList", list_id, bpy.data, "collections", scene, "collection_index")


def get_presets_folder():
    """Retrieve the base path for Blender's presets folder."""
    # Get the user scripts folder dynamically
    return os.path.join(bpy.utils.resource_path('USER'), "scripts", "presets", "operator")


def draw_properties_with_prefix(setting, layout, context, properties):
    """
    Draws properties with a * prefix if they differ between the Scene and Preferences.

    Args:
        layout (UILayout): The UI layout to draw in.
        context (Context): The Blender context.
        properties (list): List of property names to compare and draw.
    """

    prefs = context.preferences.addons[base_package].preferences

    for prop_name in properties:
        # Ensure the property exists in both Scene and Preferences
        if hasattr(setting, prop_name) and hasattr(prefs, prop_name):
            scene_value = getattr(setting, prop_name)
            pref_value = getattr(setting, prop_name)

            from ..preferences.preferenecs import PROPERTY_METADATA
            text = PROPERTY_METADATA[prop_name]["name"]

            # Determine label text with prefix
            label_prefix = "* " if scene_value != pref_value else ""
            label_text = f"{label_prefix}{text.replace('_', ' ').title()}"

            # Draw the property with dynamic label
            row = layout.row()
            row.prop(setting, prop_name, text=label_text)
        else:
            # Debugging note: Property does not exist
            print(f"Property {prop_name} not found in Scene or Preferences")


def draw_preset_settings(layout, context):
    """
    Draw the preset property dynamically based on the selected export format.
    """
    scene = context.scene
    prefs = context.preferences.addons[base_package].preferences
    export_format = scene.export_format  # Get the currently selected export format

    # Dynamically determine the property name
    prop_name = f"simple_export_preset_file_{export_format.lower()}"

    if scene.overwrite_preset_settings:
        set = scene
        label = 'Preset'

    else:  # scene.overwrite_preset_settings:
        layout.enabled = False
        set = prefs
        label = 'Default Preset'

    if hasattr(set, prop_name):
        layout.prop(set, prop_name, text=label)
    else:
        layout.label(text=f"No presets available for {export_format}", icon="ERROR")


def draw_create_export_collections(layout, context):
    scene = context.scene
    prefs = context.preferences.addons[base_package].preferences

    prop_base = context.scene

    if not scene.overwrite_collection_settings:
        layout.enabled = False
        prop_base = prefs

    # Define properties to check
    properties = [
        "collection_color",
        "filename_blend_prefix",
        "collection_prefix",
        "collection_suffix",
        "set_export_path",
        "set_preset",
    ]

    # Use the helper function to draw properties
    draw_properties_with_prefix(prop_base, layout, context, properties)

    # Collection offset
    layout.prop(prop_base, "collection_set_location_offset_on_creation")
    layout.prop(prop_base, "collection_set_root_offset_object")


def draw_filepath_settings(layout, context):
    scene = context.scene
    prefs = context.preferences.addons[base_package].preferences

    prop_base = context.scene

    if not scene.overwrite_filepath_settings:
        layout.enabled = False
        prop_base = prefs

    layout.label(text="Export Path Mode")
    row = layout.row()
    row.prop(prop_base, "export_folder_mode", expand=True)

    if prop_base.export_folder_mode == 'ABSOLUTE':
        layout.prop(prop_base, "folder_path_absolute")

    if prop_base.export_folder_mode == 'RELATIVE':
        layout.prop(prop_base, "folder_path_relative")

    if prop_base.export_folder_mode == 'MIRROR':
        layout.prop(prop_base, "folder_path_search", text="Search Path")
        layout.prop(prop_base, "folder_path_replace", text="Replacement Path")

        # Compute and display the preview
        from ..preferences.preferenecs import compute_mirror_preview
        preview_path = compute_mirror_preview(prop_base)  # Pass `self` as settings
        layout.label(text="Export Folder Preview:")
        row = layout.row(align=True)
        row.label(text=preview_path)

        if os.path.exists(preview_path):
            op = row.operator("file.external_operation", text='', icon='FILE_FOLDER')
            op.operation = 'FOLDER_OPEN'
            op.filepath = preview_path


def draw_name_settings(layout, context):
    scene = context.scene
    prefs = context.preferences.addons[base_package].preferences

    prop_base = context.scene

    if not scene.overwrite_filename_settings:
        layout.enabled = False
        prop_base = prefs
    layout.label(text="Export File Name")

    # export file name
    layout.prop(prop_base, "filename_blend_prefix")
    layout.prop(prop_base, "filename_prefix")
    layout.prop(prop_base, "filename_suffix")


def draw_custom_collection_ui(self, context):
    """Draw custom UI in the COLLECTION_PT_instancing panel."""
    layout = self.layout
    collection = context.collection

    # Add the Object Picker
    layout.prop(collection, "root_object", text="Offset Object")


def draw_operator_filepath_settings(layout, op):
    """
    Draws the export folder settings for an operator, similar to draw_filepath_settings but for operator properties.
    """
    layout.label(text="Export Path Mode")
    row = layout.row()
    row.prop(op, "export_folder_mode", expand=True)

    if op.export_folder_mode == 'ABSOLUTE':
        layout.prop(op, "folder_path_absolute")

    if op.export_folder_mode == 'RELATIVE':
        layout.prop(op, "folder_path_relative")

    if op.export_folder_mode == 'MIRROR':
        layout.prop(op, "folder_path_search", text="Search Path")
        layout.prop(op, "folder_path_replace", text="Replacement Path")

        # Compute and display the preview if possible
        try:
            from ..preferences.preferenecs import compute_mirror_preview
            preview_path = compute_mirror_preview(op)
            layout.label(text="Export Folder Preview:")
            row = layout.row(align=True)
            row.label(text=preview_path)

            import os
            if os.path.exists(preview_path):
                op_btn = row.operator("file.external_operation", text='', icon='FILE_FOLDER')
                op_btn.operation = 'FOLDER_OPEN'
                op_btn.filepath = preview_path
        except Exception:
            pass


class SIMPLE_EXPORT_menu_base:
    bl_label = ""

    def draw_header(self, context):
        layout = self.layout
        draw_simple_export_header(layout)

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        col = layout.column(align=True)
        row = col.row()
        op = row.operator("simple_export.set_presets", text="Assign Presets", icon='PRESET_NEW')
        op.outliner = False
        op.individual_collection = False

        row = col.row()
        op = row.operator("simple_export.set_export_paths", text="Assign Filepaths", icon='FOLDER_REDIRECT')
        op.outliner = False
        op.individual_collection = False

        # Get and set all properties
        props = get_set_export_paths_properties(context)

        # Set all properties
        op.export_folder_mode = props['export_folder_mode']
        op.folder_path_absolute = props['folder_path_absolute']
        op.folder_path_relative = props['folder_path_relative']
        op.folder_path_search = props['folder_path_search']
        op.folder_path_replace = props['folder_path_replace']
        op.filename_prefix = props['filename_prefix']
        op.filename_suffix = props['filename_suffix']
        op.filename_blend_prefix = props['filename_blend_prefix']

        col.separator()

        box = col.box()
        draw_pre_export_operations(box, scene)

        row = col.row()
        op = row.operator("simple_export.export_collections", text="Export Selected", icon='EXPORT')
        op.outliner = False
        op.individual_collection = False


class VIEW3D_PT_SimpleExport(SIMPLE_EXPORT_menu_base, bpy.types.Panel):
    """Creates a Panel in the Object properties window"""

    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Simple Export"
    bl_label = ""

    def draw_header(self, context):
        layout = self.layout
        draw_simple_export_header(layout)

    def draw(self, context):
        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene

        layout = self.layout
        layout.label(text="Batch Export Collections")

        # Draw format selection
        layout.prop(scene, "export_format", text="Format")

        list_id = "npanel"

        draw_export_list(layout, list_id, scene)

        # Draw Operator List
        super().draw(context)

        draw_active_list_element(layout, scene)

        draw_scene_settings_overwrite(context, layout, scene)
        draw_collection_creation(context, layout)


class SIMPLE_EXPORT_MT_context_menu(bpy.types.Menu):
    bl_label = "Custom Collection Menu"
    bl_idname = "SIMPLE_EXPORT_MT_context_menu"

    def draw(self, context):
        layout = self.layout
        row = layout.row()
        op = row.operator("scene.select_all_collections", text="Select All", icon="CHECKBOX_HLT")
        op.deselect = False
        row = layout.row()
        op = row.operator("scene.select_all_collections", text="Unselect All", icon="CHECKBOX_DEHLT")
        op.deselect = True


class SIMPLE_EXPORT_PT_CollectionExportPanel(SIMPLE_EXPORT_menu_base, bpy.types.Panel):
    bl_idname = "SCENE_PT_simple_export"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "output"

    def draw(self, context):
        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene

        layout = self.layout
        layout.label(text="Batch Export Collections")

        # Draw format selection
        layout.prop(scene, "export_format", text="Format")

        list_id = "scene"

        draw_export_list(layout, list_id, scene)

        # Draw Operator List
        super().draw(context)

        draw_active_list_element(layout, scene)

        draw_scene_settings_overwrite(context, layout, scene)
        draw_collection_creation(context, layout)


class SIMPLE_EXPORT_PT_simple_export_popup(SIMPLE_EXPORT_menu_base, bpy.types.Panel):
    bl_idname = "SIMPLE_EXPORT_PT_simple_export_popup"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_context = "empty"
    bl_ui_units_x = 45

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        row = layout.row()
        row.label(text="Simple Export Popup")

        # Export List
        row = layout.row()
        row.label(text="Export List")
        row = layout.row()

        row = layout.row(align=True)
        op = row.operator("scene.select_all_collections", text="All", icon="CHECKBOX_HLT")
        op.deselect = False
        op = row.operator("scene.select_all_collections", text="None", icon="CHECKBOX_DEHLT")
        op.deselect = True

        row = layout.row()
        row.template_list("SCENE_UL_CollectionList", "popup", bpy.data, "collections", scene, "collection_index")

        super().draw(context)


classes = (
    VIEW3D_PT_SimpleExport,
    SIMPLE_EXPORT_MT_context_menu,
    SIMPLE_EXPORT_PT_CollectionExportPanel,
    SIMPLE_EXPORT_PT_simple_export_popup,
)


# Register and Unregister
def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
