import os

import bpy


class SCENE_UL_CollectionList(bpy.types.UIList):
    """
    UIList displaying all collections with an exporter matching the selected export type.
    """

    def draw_filter(self, context, layout):
        layout.prop(context.scene, "export_format", text="Export Format")

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        prefs = context.preferences.addons[__package__].preferences
        collection = item
        if not collection:
            return

        row = layout.row(align=True)

        # Checkbox for selecting the collection for export
        row.prop(collection, "my_export_select", text="")

        # Ensure there's at least one exporter in the collection
        if not collection.exporters:
            return

        # Get exporter details
        exporter = collection.exporters[0]
        export_path = exporter.export_properties.filepath
        file_exists = os.path.exists(export_path)
        is_locked = file_exists and not os.access(export_path, os.W_OK)

        # Show lock icon based on file permissions
        if is_locked:
            icon = 'LOCKED'
        elif file_exists:
            icon = 'CURRENT_FILE'
        else:
            icon = 'FILE_NEW'

        row.label(icon=icon)
        # Map color_tag to icons
        color_tag_icons = {
            'NONE': 'OUTLINER_COLLECTION',
            'COLOR_01': 'COLLECTION_COLOR_01',
            'COLOR_02': 'COLLECTION_COLOR_02',
            'COLOR_03': 'COLLECTION_COLOR_03',
            'COLOR_04': 'COLLECTION_COLOR_04',
            'COLOR_05': 'COLLECTION_COLOR_05',
            'COLOR_06': 'COLLECTION_COLOR_06',
            'COLOR_07': 'COLLECTION_COLOR_07',
            'COLOR_08': 'COLLECTION_COLOR_08',
        }

        # Determine the icon based on the collection's color_tag
        color_tag = collection.color_tag
        icon = color_tag_icons.get(color_tag, 'OUTLINER_COLLECTION')

        # Display the collection name with the color icon
        row.label(text=collection.name, icon=icon)

        # Display the export file path as an editable property
        row.prop(exporter.export_properties, "filepath", text="", expand=True)

        # Buttons for setting the export path and opening the directory
        # Assign Path
        op = row.operator("scene.set_exporter_path", text="", icon='FOLDER_REDIRECT')
        op.collection_name = collection.name

        # TODO: Implement features
        # Assign Preset
        op = row.operator("simple_export.apply_preset", text="", icon='PRESET')
        op.collection_name = collection.name

        # Add the Export Collection button
        op = row.operator("scene.export_collection", text="", icon='EXPORT')
        op.collection_name = collection.name

    def filter_items(self, context, data, propname):
        flt_flags = []
        flt_neworder = []

        export_format = context.scene.export_format

        for collection in bpy.data.collections:
            # Filter collections based on whether they have an exporter with the matching format
            has_matching_exporter = any(
                exporter.name == export_format for exporter in collection.exporters
            )

            if has_matching_exporter:
                flt_flags.append(self.bitflag_filter_item)
            else:
                flt_flags.append(0)

        return flt_flags, flt_neworder


classes = (
    SCENE_UL_CollectionList,
)


def register():
    from bpy.utils import register_class

    bpy.types.Scene.collection_index = bpy.props.IntProperty()

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)
