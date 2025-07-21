import bpy

from ..ui.export_panels import get_operator_properties, get_set_export_paths_properties


def add_export_collections_to_menu(self, context):
    """Adds the Simple Export create export collections operator to the object context menu."""
    self.layout.separator()
    op = self.layout.operator("simple_export.create_export_collections", icon='COLLECTION_COLOR_01')
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
    op.collection_file_name_prefix = props['collection_file_name_prefix']
    op.collection_color = props['collection_color']
    op.collection_instance_offset = props['collection_instance_offset']
    op.use_root_object = props['use_root_object']
    op.preset_filepath = props['preset_filepath']
    op.export_filepath = props['export_filepath']
    op.assign_preset = props['assign_preset']
    op.assign_export_filepath = props['assign_export_filepath']
    op.export_folder_mode = path_props['export_folder_mode']
    op.folder_path_absolute = path_props['folder_path_absolute']
    op.folder_path_relative = path_props['folder_path_relative']
    op.folder_path_search = path_props['folder_path_search']
    op.folder_path_replace = path_props['folder_path_replace']
    op.filename_prefix = path_props['filename_prefix']
    op.filename_suffix = path_props['filename_suffix']
    op.filename_blend_prefix = path_props['filename_blend_prefix']


def register():
    bpy.types.VIEW3D_MT_object_context_menu.append(add_export_collections_to_menu)


def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(add_export_collections_to_menu)
