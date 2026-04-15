import bpy


def draw_custom_outliner_menu(self, context):
    layout = self.layout
    layout.separator()

    selected_element = context.id  # This determines what is selected in the Outliner

    if isinstance(selected_element, bpy.types.Collection):
        collection = selected_element
        layout.operator_context = 'INVOKE_DEFAULT'

        if len(collection.exporters) > 0:
            # Collection has exporter: export first, then filepath and preset
            op = layout.operator("simple_export.export_collections", icon='EXPORT')
            op.outliner = True
            op.individual_collection = False

            from .shared_operator_call import call_simple_export_path_ops
            call_simple_export_path_ops(context, layout, outliner=True, individual_collection=False, icon='NONE')

            from .shared_operator_call import call_assign_preset_op
            call_assign_preset_op(context, layout, outliner=True, icon='NONE', collection_name=collection.name)

            op = layout.operator("simple_export.remove_exporters", icon='TRASH')
            op.collection_name = collection.name
        else:
            # No exporter assigned: show assign exporter first
            from .shared_operator_call import call_simple_add_exporter_to_collection
            call_simple_add_exporter_to_collection(context, collection, layout)

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
