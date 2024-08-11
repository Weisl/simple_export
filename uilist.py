import os
import bpy


class SCENE_UL_CollectionList(bpy.types.UIList):
    """
    UIList displaying all collections with an exporter matching the selected export type.
    """

    def draw_filter(self, context, layout):
        layout.prop(context.scene, "export_format", text="Export Format")
        row = layout.row(align=True)
        row.operator("scene.select_all_collections", text="Select All", icon='CHECKBOX_HLT')
        row.operator("scene.unselect_all_collections", text="Unselect All", icon='CHECKBOX_DEHLT')

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        prefs = context.preferences.addons[__package__].preferences
        collection = item
        if not collection:
            return

        row = layout.row(align=True)

        # Checkbox as the first item
        row.prop(collection, "my_export_select", text="")

        exporter = collection.exporters[0]
        export_path = exporter.export_properties.filepath
        file_exists = os.path.exists(export_path)
        is_locked = file_exists and not os.access(export_path, os.W_OK)

        # Conditionally show icons based on preferences
        if prefs.show_lock_icons:
            lock_icon = 'LOCKED' if is_locked else 'UNLOCKED'
            row.label(icon=lock_icon)

        if prefs.show_edit_icons:
            file_icon = 'CURRENT_FILE' if file_exists else 'FILE_NEW'
            row.label(icon=file_icon)

        # Display collection name
        row.label(text=collection.name, icon='OUTLINER_COLLECTION')
        # Display collection name as a prop
        # row.prop(collection, "name", text="", icon='OUTLINER_COLLECTION')

        # Filepath with more space
        # row.label(text=export_path)  # Full path as a label
        row.prop(exporter.export_properties, "filepath", text="", expand=True)  # Filename as editable prop

        # Buttons for setting export path and opening the directory
        op = row.operator("scene.set_exporter_path", text="", icon='FILE_REFRESH')
        op.collection_name = collection.name

        if not file_exists:
            op = row.operator("scene.create_export_directory", text="", icon='FILE_FOLDER')
            op.collection_name = collection.name

        # Add the Export Collection button
        op = row.operator("scene.export_collection", text="", icon='EXPORT')
        op.collection_name = collection.name

    def filter_items(self, context, data, propname):
        flt_flags = []
        flt_neworder = []

        export_format = context.scene.export_format

        for i, collection in enumerate(bpy.data.collections):
            # Filter out collections without exporters or without matching exporters
            has_matching_exporter = any(
                exporter.name == export_format for exporter in collection.exporters
            )

            if has_matching_exporter:
                flt_flags.append(self.bitflag_filter_item)
            else:
                flt_flags.append(0)

        return flt_flags, flt_neworder
