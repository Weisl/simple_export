import bpy


def draw_custom_outliner_menu(self, context):
    layout = self.layout
    layout.separator()

    selected_element = context.id  # The active item; may be part of a larger Outliner selection

    if isinstance(selected_element, bpy.types.Collection):
        collection = selected_element
        layout.operator_context = 'INVOKE_DEFAULT'

        from ..functions.outliner_func import get_outliner_collections
        outliner_collections = get_outliner_collections(context)
        if collection not in outliner_collections:
            outliner_collections = [collection]

        has_exporter = any(len(c.exporters) > 0 for c in outliner_collections)
        missing_exporter = any(len(c.exporters) == 0 for c in outliner_collections)

        if has_exporter:
            # At least one selected collection already has an exporter: export, filepath and preset
            op = layout.operator("simple_export.export_collections", icon='EXPORT')
            op.outliner = True
            op.individual_collection = False

            from .shared_operator_call import call_simple_export_path_ops
            call_simple_export_path_ops(context, layout, outliner=True, individual_collection=False, icon='NONE')

            from .shared_operator_call import call_assign_preset_op
            call_assign_preset_op(context, layout, outliner=True, icon='NONE', collection_name=collection.name)

            op = layout.operator("simple_export.remove_exporters", icon='TRASH')
            op.outliner = True
            op.collection_name = collection.name

        if missing_exporter:
            # At least one selected collection has no exporter yet: offer to add one to the whole selection
            from .shared_operator_call import call_simple_add_exporter_to_collection
            call_simple_add_exporter_to_collection(context, collection, layout, outliner=True)

    elif isinstance(selected_element, bpy.types.Object):
        scene = context.scene
        layout.operator_context = 'INVOKE_DEFAULT'
        from .shared_operator_call import call_create_export_collection_op
        call_create_export_collection_op(scene, layout)


classes = ()


def register():
    bpy.types.OUTLINER_MT_collection.append(draw_custom_outliner_menu)
    bpy.types.OUTLINER_MT_object.append(draw_custom_outliner_menu)


def unregister():
    bpy.types.OUTLINER_MT_collection.remove(draw_custom_outliner_menu)
    bpy.types.OUTLINER_MT_object.remove(draw_custom_outliner_menu)
