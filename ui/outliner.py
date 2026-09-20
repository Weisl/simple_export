import bpy


class SIMPLE_EXPORT_MT_outliner_context_menu(bpy.types.Menu):
    """Simple Export submenu of the Outliner collection and object context menus"""
    bl_idname = "SIMPLE_EXPORT_MT_outliner_context_menu"
    bl_label = "Simple Export"

    def draw(self, context):
        layout = self.layout
        layout.operator_context = 'INVOKE_DEFAULT'

        selected_element = context.id  # The active item; may be part of a larger Outliner selection

        if isinstance(selected_element, bpy.types.Collection):
            collection = selected_element

            from ..functions.outliner_func import get_outliner_collections
            outliner_collections = get_outliner_collections(context)
            if collection not in outliner_collections:
                outliner_collections = [collection]

            has_exporter = any(len(c.exporters) > 0 for c in outliner_collections)
            missing_exporter = any(len(c.exporters) == 0 for c in outliner_collections)

            if has_exporter:
                # At least one selected collection already has an exporter: export, filepath and preset
                op = layout.operator("simple_export.export_collections", icon='NONE')
                op.outliner = True
                op.individual_collection = False

                from .shared_operator_call import call_simple_export_path_ops
                call_simple_export_path_ops(context, layout, outliner=True, individual_collection=False, icon='NONE')

                from .shared_operator_call import call_assign_preset_op
                call_assign_preset_op(context, layout, outliner=True, icon='NONE', collection_name=collection.name)

                # Copy from the right-clicked collection to the other selected ones; greyed out until
                # a second collection is selected so the entry stays discoverable
                if len(collection.exporters) > 0:
                    other_collections = [c for c in outliner_collections if c != collection]
                    row = layout.row()
                    row.enabled = bool(other_collections)
                    op = row.operator("simple_export.copy_export_settings", icon='NONE')
                    op.source_name = collection.name

                op = layout.operator("simple_export.remove_exporters", icon='NONE')
                op.outliner = True
                op.collection_name = collection.name

            if missing_exporter:
                # At least one selected collection has no exporter yet: offer to add one to the whole selection
                from .shared_operator_call import call_simple_add_exporter_to_collection
                call_simple_add_exporter_to_collection(context, collection, layout, outliner=True, icon='NONE')

        elif isinstance(selected_element, bpy.types.Object):
            from .shared_operator_call import call_create_export_collection_op
            call_create_export_collection_op(context.scene, layout, icon='NONE')


def draw_custom_outliner_menu(self, context):
    """Adds the Simple Export submenu to the Outliner collection and object context menus."""
    if isinstance(context.id, (bpy.types.Collection, bpy.types.Object)):
        self.layout.separator()
        self.layout.menu(SIMPLE_EXPORT_MT_outliner_context_menu.bl_idname, icon='EXPORT')


classes = (
    SIMPLE_EXPORT_MT_outliner_context_menu,
)


def register():
    from bpy.utils import register_class

    for cls in classes:
        register_class(cls)

    bpy.types.OUTLINER_MT_collection.append(draw_custom_outliner_menu)
    bpy.types.OUTLINER_MT_object.append(draw_custom_outliner_menu)


def unregister():
    from bpy.utils import unregister_class

    bpy.types.OUTLINER_MT_collection.remove(draw_custom_outliner_menu)
    bpy.types.OUTLINER_MT_object.remove(draw_custom_outliner_menu)

    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
