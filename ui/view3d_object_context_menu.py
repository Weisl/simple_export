import bpy


def add_export_collections_to_menu(self, context):
    """Adds the Simple Export create export collections operator to the object context menu."""
    scene = context.scene

    self.layout.separator()
    self.layout.operator_context = 'INVOKE_DEFAULT'
    from .shared_operator_call import call_create_export_collection_op
    op = call_create_export_collection_op(scene, self.layout)

    # Set default properties
    # op.only_selection = True
    op.collection_naming_overwrite = False
    op.collection_name_new = ""


def register():
    bpy.types.VIEW3D_MT_object_context_menu.append(add_export_collections_to_menu)


def unregister():
    bpy.types.VIEW3D_MT_object_context_menu.remove(add_export_collections_to_menu)
