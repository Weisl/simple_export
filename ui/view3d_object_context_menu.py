import bpy
from ..ui.export_panels import get_operator_properties, get_set_export_paths_properties

def add_export_collections_to_menu(self, context):
    """Adds the Simple Export create export collections operator to the object context menu."""
    self.layout.separator()
    op = self.layout.operator("simple_export.create_export_collections", icon='COLLECTION_COLOR_01')
    # Set default properties
    op.only_selection = True
    op.overwrite_naming = False
    op.overwrite_collection_name = ""
    op.use_numbering = False
    op.parent_collection_name = context.scene.parent_collection.name if context.scene.parent_collection else ""
    # Get and set properties from preferences/scene
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

def register():
    bpy.types.VIEW3D_MT_object_context_menu.append(add_export_collections_to_menu)

def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(add_export_collections_to_menu) 