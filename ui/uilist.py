import os

import bpy

from .. import __package__ as base_package
from ..core.export_formats import ExportFormats
from ..core.info import COLOR_TAG_ICONS
from ..functions.exporter_funcs import find_exporter
from ..functions.path_utils import clean_relative_path


class SCENE_UL_CollectionList(bpy.types.UIList):
    """
    UIList displaying all collections with an exporter matching the selected export type.
    """

    def draw_filter(self, context, layout):
        layout.prop(context.window_manager, "export_format", text="Filter Format")

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        prefs = context.preferences.addons[base_package].preferences

        # Determine settings based on the list_id
        if self.list_id == "scene":
            settings = prefs.scene_properties
        elif self.list_id == "npanel":
            settings = prefs.npanel_properties
        else:  # popup":
            settings = prefs.popup_properties

        collection = item
        if not collection:
            return

        row = layout.row(align=True)

        # Checkbox for selecting the collection for export
        row.prop(collection, "simple_export_selected", text="")

        # Ensure there's at least one exporter in the collection
        if not collection.exporters:
            return

        # Get exporter details
        scene = context.scene

        exporter = find_exporter(collection, scene.export_format)
        export_path = exporter.export_properties.filepath
        export_path = clean_relative_path(export_path)
        file_exists = os.path.exists(export_path)
        is_locked = file_exists and not os.access(export_path, os.W_OK)

        if settings.uilist_icon:
            # Show lock icon based on file permissions
            if is_locked:
                icon = 'LOCKED'
            elif file_exists:
                icon = 'CURRENT_FILE'
            else:
                icon = 'FILE_NEW'

            row.label(icon=icon)

        # Determine the icon based on the collection's color_tag
        color_tag = collection.color_tag
        icon = COLOR_TAG_ICONS.get(color_tag, 'OUTLINER_COLLECTION')

        # Display the collection name with the color icon
        row.label(text=collection.name, icon=icon)

        if settings.uilist_show_filepath:
            # Display the export file path as an editable property
            row.prop(exporter.export_properties, "filepath", text="", expand=True)

        if settings.uilist_set_filepath:
            # Buttons for setting the export path and opening the directory
            # Assign Path
            op = row.operator("simple_export.set_export_paths", text="", icon='FOLDER_REDIRECT')
            op.outliner = False
            op.individual_collection = True
            op.collection_name = collection.name

        if settings.uilist_set_preset:
            # Assign Preset
            op = row.operator("simple_export.assign_presets", text="", icon='PRESET')
            op.collection_name = collection.name

        # Add the Export Collection button
        op = row.operator("simple_export.export_collections", text="", icon='EXPORT')
        op.outliner = False
        op.individual_collection = True
        op.collection_name = collection.name

    def filter_items(self, context, data, propname):
        flt_flags = []
        flt_neworder = []

        scene = context.scene

        export_format = scene.export_format
        export_format_obj = ExportFormats.get(export_format)

        for collection in bpy.data.collections:
            # Filter collections based on whether they have an exporter with the matching format
            has_matching_exporter = any(
                str(type(exporter.export_properties)) == export_format_obj.op_type for exporter in
                collection.exporters
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
