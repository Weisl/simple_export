import bpy

from .export_panels import SIMPLE_EXPORT_menu_base


class SIMPLE_EXPORT_PT_simple_export_popup(SIMPLE_EXPORT_menu_base, bpy.types.Panel):
    bl_idname = "SIMPLE_EXPORT_PT_simple_export_popup"
    bl_space_type = "VIEW_3D"
    bl_region_type = "WINDOW"
    bl_context = "empty"
    bl_ui_units_x = 45

    list_id = "popup"

    def draw(self, context):
        scene = context.scene
        layout = self.layout

        # row = layout.row()
        # row.label(text="Simple Export Popup")
        #
        # row = layout.row()
        # draw Create exporter
        # from .shared_operator_call import call_create_export_collection_op
        # call_create_export_collection_op(scene, row)
        #
        # # Export List
        # row = layout.row()
        #
        # row = layout.row(align=True)
        # op = row.operator("scene.select_all_collections", text="All", icon="CHECKBOX_HLT")
        # op.deselect = False
        # op = row.operator("scene.select_all_collections", text="None", icon="CHECKBOX_DEHLT")
        # op.deselect = True

        # draw Export List
        from .shared_draw import draw_export_list
        draw_export_list(layout, self.list_id, scene)

        super().draw(context)


classes = (
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
