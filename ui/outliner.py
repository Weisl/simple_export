import bpy


def draw_custom_outliner_menu(self, context):
    layout = self.layout
    layout.separator()

    selected_element = context.id  # This determines what is selected in the Outliner

    if isinstance(selected_element, bpy.types.Collection):
        # Show full export menu for collections
        layout.menu(CUSTOM_MT_outliner_simple_export_menu.bl_idname, icon='EXPORT')
    elif isinstance(selected_element, bpy.types.Object):
        # Show only 'Create Export Collections' for objects
        op = layout.operator('simple_export.create_export_collections', text="Create Export Collections",
                        icon='COLLECTION_COLOR_01')
        
        # Set default properties
        op.only_selection = True
        op.overwrite_naming = False
        op.overwrite_collection_name = ""
        op.use_numbering = False
        op.parent_collection_name = context.scene.parent_collection.name if context.scene.parent_collection else ""
        
        # Get and set properties from preferences/scene
        from .export_panels import get_operator_properties, get_set_export_paths_properties
        props = get_operator_properties(context)
        path_props = get_set_export_paths_properties(context)
        op.collection_custom_prefix = props['collection_custom_prefix']
        op.collection_custom_suffix = props['collection_custom_suffix']
        op.collection_file_name_prefix = props['collection_file_name_prefix']
        op.collection_color = props['collection_color']
        op.collection_instance_offset = props['collection_instance_offset']
        op.use_root_object = props['use_root_object']
        op.preset_filepath = props['preset_filepath']
        op.export_filepath = props['export_filepath']
        op.assign_preset = props['assign_preset']
        op.assign_export_filepath = props['assign_export_filepath']
        op.export_folder_mode = path_props['export_folder_mode']
        op.absolute_export_path = path_props['absolute_export_path']
        op.relative_export_path = path_props['relative_export_path']
        op.mirror_search_path = path_props['mirror_search_path']
        op.mirror_replacement_path = path_props['mirror_replacement_path']
        op.filename_custom_prefix = path_props['filename_custom_prefix']
        op.filename_custom_suffix = path_props['filename_custom_suffix']
        op.filename_file_name_prefix = path_props['filename_file_name_prefix']


class CUSTOM_MT_outliner_simple_export_menu(bpy.types.Menu):
    bl_label = "Simple Export"
    bl_idname = "CUSTOM_MT_outliner_simple_export_menu"

    def draw(self, context):
        layout = self.layout
        collection = context.id  # Ensure we reference the selected collection

        if not isinstance(collection, bpy.types.Collection):
            return

        layout.operator('simple_export.add_settings_to_collections', icon='COLLECTION_COLOR_01')

        layout.separator()
        op = layout.operator("simple_export.export_collections", icon='EXPORT')
        op.outliner = True
        op.individual_collection = False

        op = layout.operator("simple_export.assign_presets", icon='PRESET_NEW')
        op.outliner = True
        op.individual_collection = False

        op = layout.operator("simple_export.set_export_paths", text="Assign Filepaths", icon='FOLDER_REDIRECT')
        op.outliner = True
        op.individual_collection = False
        
        # Get and set all properties
        from .export_panels import get_set_export_paths_properties
        props = get_set_export_paths_properties(context)
        
        # Set all properties
        op.export_folder_mode = props['export_folder_mode']
        op.absolute_export_path = props['absolute_export_path']
        op.relative_export_path = props['relative_export_path']
        op.mirror_search_path = props['mirror_search_path']
        op.mirror_replacement_path = props['mirror_replacement_path']
        op.filename_custom_prefix = props['filename_custom_prefix']
        op.filename_custom_suffix = props['filename_custom_suffix']
        op.filename_file_name_prefix = props['filename_file_name_prefix']

        # Open Popup window
        layout.operator("wm.call_panel", text="Open Export Popup",
                        icon='WINDOW').name = "SIMPLE_EXPORT_PT_simple_export_popup"


classes = (
    CUSTOM_MT_outliner_simple_export_menu,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.types.OUTLINER_MT_collection.append(draw_custom_outliner_menu)
    bpy.types.OUTLINER_MT_object.append(draw_custom_outliner_menu)  # Ensure it appears for objects too


def unregister():
    bpy.types.OUTLINER_MT_collection.remove(draw_custom_outliner_menu)
    bpy.types.OUTLINER_MT_object.remove(draw_custom_outliner_menu)

    from bpy.utils import unregister_class
    for cls in reversed(classes):
        unregister_class(cls)
