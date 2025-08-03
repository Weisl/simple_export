import os

import bpy

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
    prefs = context.preferences.addons[base_package].preferences
    scene = context.scene
    
    # Collection settings - use scene if overwrite is enabled, else prefs
    collection_settings = scene if scene.overwrite_collection_settings else prefs
    op.collection_prefix = collection_settings.collection_prefix
    op.collection_suffix = collection_settings.collection_suffix
    op.filename_blend_prefix = collection_settings.collection_blend_prefix
    op.collection_color = collection_settings.collection_color
    op.collection_instance_offset = collection_settings.collection_set_location_offset_on_creation
    op.use_root_object = collection_settings.collection_use_root_offset_object
    
    # Preset and export path settings
    op.set_preset = scene.set_preset
    op.set_export_path = scene.set_export_path
    
    # Get preset filepath if auto-set is enabled
    op.preset_filepath = ""
    if scene.set_preset:
        export_format = scene.export_format.lower()
        prop_name = f"simple_export_preset_file_{export_format}"
        preset_settings = scene if scene.overwrite_preset_settings else prefs
        op.preset_filepath = getattr(preset_settings, prop_name, "")
    
    # Filepath settings - use scene if overwrite is enabled, else prefs
    filepath_settings = scene if scene.overwrite_filepath_settings else prefs
    op.export_folder_mode = filepath_settings.export_folder_mode
    op.folder_path_absolute = filepath_settings.folder_path_absolute
    op.folder_path_relative = filepath_settings.folder_path_relative
    op.folder_path_search = filepath_settings.folder_path_search
    op.folder_path_replace = filepath_settings.folder_path_replace
    
    # Filename settings - use scene if overwrite is enabled, else prefs
    filename_settings = scene if scene.overwrite_filename_settings else prefs
    op.filename_prefix = filename_settings.filename_prefix
    op.filename_suffix = filename_settings.filename_suffix
    op.filename_blend_prefix = filename_settings.filename_blend_prefix


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
        prefs = context.preferences.addons[base_package].preferences
        
        # Filepath Settings
        row = body.row()
        row.prop(scene, 'overwrite_filepath_settings')
        box = body.box()
        filepath_settings = scene if scene.overwrite_filepath_settings else prefs
        if scene.overwrite_filepath_settings:
            box.enabled = True
        else:
            box.enabled = False
            
        # Draw filepath properties
        box.label(text="Export Path Mode")
        is_file_saved = bool(bpy.data.filepath)
        row = box.row()
        row.prop(filepath_settings, "export_folder_mode", expand=True)
        if not is_file_saved:
            row.enabled = False
            box.label(text="Save the blend file to use filepath modes", icon='INFO')
        if filepath_settings.export_folder_mode == 'ABSOLUTE':
            box.prop(filepath_settings, "folder_path_absolute")
        if filepath_settings.export_folder_mode == 'RELATIVE':
            box.prop(filepath_settings, "folder_path_relative")
        if filepath_settings.export_folder_mode == 'MIRROR':
            box.prop(filepath_settings, "folder_path_search", text="Search Path")
            box.prop(filepath_settings, "folder_path_replace", text="Replacement Path")
            try:
                from ..preferences.preferenecs import compute_mirror_preview
                preview_path = compute_mirror_preview(filepath_settings)
                box.label(text="Export Folder Preview:")
                row = box.row(align=True)
                row.label(text=preview_path)
                import os
                if os.path.exists(preview_path):
                    op_btn = row.operator("file.external_operation", text='', icon='FILE_FOLDER')
                    op_btn.operation = 'FOLDER_OPEN'
                    op_btn.filepath = preview_path
            except Exception:
                pass

        # Filename Settings
        row = body.row()
        row.prop(scene, 'overwrite_filename_settings')
        box = body.box()
        filename_settings = scene if scene.overwrite_filename_settings else prefs
        if scene.overwrite_filename_settings:
            box.enabled = True
        else:
            box.enabled = False
            
        # Draw filename properties
        box.label(text="File Name Settings")
        box.prop(filename_settings, "filename_prefix")
        box.prop(filename_settings, "filename_suffix")
        box.prop(filename_settings, "filename_blend_prefix")

        # Preset Settings
        row = body.row()
        row.prop(scene, 'overwrite_preset_settings')
        box = body.box()
        preset_settings = scene if scene.overwrite_preset_settings else prefs
        if scene.overwrite_preset_settings:
            box.enabled = True
        else:
            box.enabled = False
            
        # Draw preset properties
        box.label(text="Export Preset")
        export_format = scene.export_format
        prop_name = f"simple_export_preset_file_{export_format.lower()}"
        if hasattr(preset_settings, prop_name):
            label = 'Preset' if scene.overwrite_preset_settings else 'Default Preset'
            box.prop(preset_settings, prop_name, text=label)
        else:
            box.label(text=f"No presets available for {export_format}", icon="ERROR")

        # Collection Settings
        row = body.row()
        row.prop(scene, 'overwrite_collection_settings')
        box = body.box()
        collection_settings = scene if scene.overwrite_collection_settings else prefs
        if scene.overwrite_collection_settings:
            box.enabled = True
        else:
            box.enabled = False
            
        # Draw collection name properties
        box.label(text="Collection Name")
        if getattr(collection_settings, "collection_naming_overwrite", None):
            box.prop(collection_settings, "collection_naming_overwrite")
            if collection_settings.collection_naming_overwrite:
                box.prop(collection_settings, "collection_name_new")
                box.prop(collection_settings, "use_numbering")
        box.prop(collection_settings, "collection_blend_prefix")
        box.prop(collection_settings, "collection_prefix")
        box.prop(collection_settings, "collection_suffix")
        
        # Draw collection settings properties
        box.label(text="Collection Settings")
        box.prop_search(collection_settings, "parent_collection_name", bpy.data, "collections")
        box.prop(collection_settings, "collection_color")
        box.prop(collection_settings, "collection_instance_offset")
        box.prop(collection_settings, "use_root_object")


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

            # Get and set properties from preferences/scene
            prefs = context.preferences.addons[base_package].preferences
            scene = context.scene
            
            # Filepath settings - use scene if overwrite is enabled, else prefs
            filepath_settings = scene if scene.overwrite_filepath_settings else prefs
            op.export_folder_mode = filepath_settings.export_folder_mode
            op.folder_path_absolute = filepath_settings.folder_path_absolute
            op.folder_path_relative = filepath_settings.folder_path_relative
            op.folder_path_search = filepath_settings.folder_path_search
            op.folder_path_replace = filepath_settings.folder_path_replace
            
            # Filename settings - use scene if overwrite is enabled, else prefs
            filename_settings = scene if scene.overwrite_filename_settings else prefs
            op.filename_prefix = filename_settings.filename_prefix
            op.filename_suffix = filename_settings.filename_suffix
            op.filename_blend_prefix = filename_settings.filename_blend_prefix

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


def draw_custom_collection_ui(self, context):
    """Draw custom UI in the COLLECTION_PT_instancing panel."""
    layout = self.layout
    collection = context.collection

    # Add the Object Picker
    layout.prop(collection, "root_object", text="Offset Object")





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

        # Get and set properties from preferences/scene
        prefs = context.preferences.addons[base_package].preferences
        scene = context.scene
        
        # Filepath settings - use scene if overwrite is enabled, else prefs
        filepath_settings = scene if scene.overwrite_filepath_settings else prefs
        op.export_folder_mode = filepath_settings.export_folder_mode
        op.folder_path_absolute = filepath_settings.folder_path_absolute
        op.folder_path_relative = filepath_settings.folder_path_relative
        op.folder_path_search = filepath_settings.folder_path_search
        op.folder_path_replace = filepath_settings.folder_path_replace
        
        # Filename settings - use scene if overwrite is enabled, else prefs
        filename_settings = scene if scene.overwrite_filename_settings else prefs
        op.filename_prefix = filename_settings.filename_prefix
        op.filename_suffix = filename_settings.filename_suffix
        op.filename_blend_prefix = filename_settings.filename_blend_prefix

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
