import os

import bpy

from ..core.export_formats import ExportFormats
from ..core.info import COLOR_TAG_ICONS
from ..functions.exporter_funcs import find_exporter
from ..functions.path_utils import clean_relative_path


def collection_name_mismatch(base_name, export_path):
    """Check if the collection name does not match the export file name exactly."""
    export_filename = os.path.splitext(os.path.basename(export_path))[0]

    return base_name != export_filename


class OBJECT_OT_root_object_actions(bpy.types.Operator):
    """Perform actions on the root object"""
    bl_idname = "object.root_object_actions"
    bl_label = "Root Object Actions"

    action: bpy.props.StringProperty()
    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        collection_name = self.collection_name
        collection = bpy.data.collections.get(collection_name)

        if not collection:
            self.report({'ERROR'}, f"Collection '{collection_name}' not found")
            return {'CANCELLED'}

        if self.action == "remove":
            collection.root_object = None
            self.report({'INFO'}, "Root object removed")

        elif self.action == "select_root":
            obj = collection.root_object
            if obj and obj.name in context.scene.objects:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                context.view_layer.objects.active = obj
                self.report({'INFO'}, f"Selected root object: {obj.name}")
            else:
                self.report({'WARNING'}, "Root object not found in scene")

        elif self.action == "select_content":
            bpy.ops.object.select_all(action='DESELECT')
            for obj in collection.objects:
                obj.select_set(True)
            self.report({'INFO'}, f"Selected all objects in collection '{collection.name}'")

        elif self.action == "unhide_content":
            for obj in collection.objects:
                obj.hide_set(False)
            self.report({'INFO'}, f"Unhid all objects in collection '{collection.name}'")

        elif self.action == "hide_content":
            for obj in collection.objects:
                obj.hide_set(True)
            self.report({'INFO'}, f"Hid all objects in collection '{collection.name}'")

        else:
            self.report({'ERROR'}, "Unknown action")

        return {'FINISHED'}


class OBJECT_OT_set_menu_collection(bpy.types.Operator):
    """Set the collection name and open the menu"""
    bl_idname = "object.set_menu_collection"
    bl_label = "Set Menu Collection"

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        context.scene.menu_collection_name = self.collection_name
        bpy.ops.wm.call_menu(name="EXPORT_MT_root_object_menu")
        return {'FINISHED'}


class EXPORT_MT_root_object_menu(bpy.types.Menu):
    """Root Object Action Menu"""
    bl_idname = "EXPORT_MT_root_object_menu"
    bl_label = "Collection Actions"

    def draw(self, context):
        layout = self.layout
        collection_name = context.scene.menu_collection_name

        op = layout.operator("object.root_object_actions", text="Remove Root Object", icon='X')
        op.action = "remove"
        op.collection_name = collection_name

        op = layout.operator("object.root_object_actions", text="Select Root Object",
                             icon='RESTRICT_SELECT_OFF')
        op.action = "select_root"
        op.collection_name = collection_name

        layout.separator()

        op = layout.operator("object.root_object_actions", text="Select Collection Content",
                             icon='OUTLINER_COLLECTION')
        op.action = "select_content"
        op.collection_name = collection_name

        op = layout.operator("object.root_object_actions", text="Hide Collection Content",
                             icon='HIDE_ON')
        op.action = "hide_content"
        op.collection_name = collection_name

        op = layout.operator("object.root_object_actions", text="Unide Collection Content",
                             icon='HIDE_OFF')
        op.action = "unhide_content"
        op.collection_name = collection_name

        layout.separator()

        from .shared_operator_call import call_simple_export_path_ops
        op = call_simple_export_path_ops(context, layout, outliner=False,
                                         individual_collection=True, collection_name=collection_name)

        op = layout.operator("simple_export.set_presets", icon='PRESET')
        op.outliner = False
        op.individual_collection = True
        op.collection_name = collection_name

        op = layout.operator("simple_export.open_exporter_in_properties", icon='PROPERTIES')
        op.collection_name = collection_name


class OBJECT_OT_select_root(bpy.types.Operator):
    """Select the root object"""
    bl_idname = "object.select_root"
    bl_label = "Select Root Object"

    collection_name: bpy.props.StringProperty()

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if collection and collection.root_object:
            obj = collection.root_object
            # Check if object is present by name
            if obj.name in context.scene.objects:
                bpy.ops.object.select_all(action='DESELECT')
                obj.select_set(True)
                context.view_layer.objects.active = obj
                self.report({'INFO'}, f"Selected root object: {obj.name}")
            else:
                self.report({'WARNING'}, "Root object not found in the active scene")
        else:
            self.report({'WARNING'}, "No root object assigned")
        return {'FINISHED'}


class SCENE_UL_CollectionList(bpy.types.UIList):
    """
    UIList displaying all collections with an exporter matching the selected export type.
    """

    def draw_filter(self, context, layout):
        layout.prop(context.window_manager, "export_format", text="Filter Format")

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        from .. import __package__ as base_package
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

            from .shared_operator_call import call_simple_export_path_ops
            op = call_simple_export_path_ops(context, row, text='', outliner=False,
                                             individual_collection=True, collection_name=collection.name)

        if settings.uilist_set_preset:
            # Assign Preset
            op = row.operator("simple_export.set_presets", text="", icon='PRESET')
            op.outliner = False
            op.individual_collection = True
            op.collection_name = collection.name

        if collection.use_root_object:
            # Display Empty or Eyedropper button depending on the root_object state
            if collection.use_root_object and collection.root_object:
                op = row.operator("object.select_root", text="", icon='EMPTY_AXIS')
                op.collection_name = collection.name
            else:
                row.prop(collection, "root_object", text="")

        # Add arrow button that sets the collection name and opens the menu
        arrow_op = row.operator("object.set_menu_collection", text="", icon='TRIA_DOWN')
        arrow_op.collection_name = collection.name

        from ..core.export_path_func import generate_base_name

        filename_settings = scene
        base_name = generate_base_name(collection.name, filename_settings.filename_prefix,
                                       filename_settings.filename_suffix, filename_settings.filename_blend_prefix)

        if exporter.export_properties.filepath and collection_name_mismatch(base_name, export_path):
            op = row.operator("simple_export.fix_export_filename", text="", icon='ERROR')
            op.collection_name = collection.name
            op.filename_prefix = filename_settings.filename_prefix
            op.filename_suffix = filename_settings.filename_suffix
            op.filename_blend_prefix = filename_settings.filename_blend_prefix

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
    OBJECT_OT_select_root,
    EXPORT_MT_root_object_menu,
    OBJECT_OT_set_menu_collection,
    OBJECT_OT_root_object_actions,
)


def register():
    from bpy.utils import register_class

    bpy.types.Scene.collection_index = bpy.props.IntProperty()
    bpy.types.Scene.menu_collection_name = bpy.props.StringProperty(
        name="Menu Collection Name",
        description="Temporary storage for collection name"
    )

    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class

    for cls in reversed(classes):
        unregister_class(cls)

    # Remove Scene properties
    del bpy.types.Scene.menu_collection_name
