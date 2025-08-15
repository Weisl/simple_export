import bpy


def draw_custom_outliner_menu(self, context):
    layout = self.layout
    layout.separator()

    selected_element = context.id  # This determines what is selected in the Outliner

    if isinstance(selected_element, bpy.types.Collection):
        # Show full export menu for collections
        layout.menu(CUSTOM_MT_outliner_simple_export_menu.bl_idname, icon='EXPORT')
    elif isinstance(selected_element, bpy.types.Object):
        scene = context.scene
        from .shared_operator_call import call_create_export_collection_op
        op = call_create_export_collection_op(scene, layout)


class CUSTOM_MT_outliner_simple_export_menu(bpy.types.Menu):
    bl_label = "Simple Export"
    bl_idname = "CUSTOM_MT_outliner_simple_export_menu"

    def draw(self, context):
        layout = self.layout
        collection = context.id  # Ensure we reference the selected collection

        if not isinstance(collection, bpy.types.Collection):
            return

        from .shared_operator_call import call_simple_add_exporter_to_collection
        call_simple_add_exporter_to_collection(context, collection, layout)

        layout.separator()
        op = layout.operator("simple_export.export_collections", icon='EXPORT')
        op.outliner = True
        op.individual_collection = False

        op = layout.operator("simple_export.assign_presets", icon='PRESET_NEW')
        op.outliner = True
        op.individual_collection = False

        from .shared_operator_call import call_simple_export_path_ops
        op = call_simple_export_path_ops(context, layout, collection, outliner=True,
                                         individual_collection=False)

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
