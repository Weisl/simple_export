import bpy


class SIMPLE_EXPORT_MT_object_context_menu(bpy.types.Menu):
    """Simple Export submenu of the 3D viewport object context menu"""
    bl_idname = "SIMPLE_EXPORT_MT_object_context_menu"
    bl_label = "Simple Export"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'

        from .shared_operator_call import call_create_export_collection_op
        call_create_export_collection_op(context.scene, layout, icon='NONE')

        layout.operator("simple_export.create_instance_collection")


def draw_simple_export_submenu(self, context):
    """Adds the Simple Export submenu to the object context menu."""
    self.layout.separator()
    self.layout.menu(SIMPLE_EXPORT_MT_object_context_menu.bl_idname, icon='EXPORT')


classes = (
    SIMPLE_EXPORT_MT_object_context_menu,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    bpy.types.VIEW3D_MT_object_context_menu.append(draw_simple_export_submenu)


def unregister():
    from bpy.utils import unregister_class

    bpy.types.VIEW3D_MT_object_context_menu.remove(draw_simple_export_submenu)

    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
