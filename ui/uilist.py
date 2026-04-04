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

        # Exporter actions
        from .shared_operator_call import call_simple_export_path_ops
        op = call_simple_export_path_ops(context, layout, outliner=False,
                                         individual_collection=True, collection_name=collection_name)

        from .shared_operator_call import call_assign_preset_op
        call_assign_preset_op(context, layout, individual_collection=True, collection_name=collection_name)

        op = layout.operator("simple_export.remove_exporters", icon='X')
        op.collection_name = collection_name
        layout.separator()

        # Root Object Actions
        op = layout.operator("object.root_object_actions", text="Remove Root Object", icon='X')
        op.action = "remove"
        op.collection_name = collection_name

        op = layout.operator("object.root_object_actions", text="Select Root Object",
                             icon='RESTRICT_SELECT_OFF')
        op.action = "select_root"
        op.collection_name = collection_name

        # Selection and visibility actions
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

        # Open Exporter in Properties
        layout.separator()
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
        pass

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        # Determine settings based on the list_id

        collection = item
        if not collection:
            return

        # Ensure there's at least one exporter in the collection
        if not collection.exporters:
            return

        # Get exporter details
        scene = context.scene
        format_filter = scene.export_format_filter if scene.use_filter else None
        exporter = find_exporter(collection, format_filter=format_filter)

        export_path = exporter.export_properties.filepath
        export_path = clean_relative_path(export_path)
        file_exists = os.path.exists(export_path)

        ### POPUP UI ###

        if self.list_id == 'popup':
            # Status Name Filepath
            from .shared_draw import get_table_columns
            col_01, col_02, col_03, col_04, col_05 = get_table_columns(layout)

            ########## Status
            row = col_01.row(align=False)
            # Checkbox
            row.prop(collection, "simple_export_selected", text="")
            # Status Icon
            icon = self.get_export_status_icon(export_path, file_exists)
            row.label(text='', icon=icon)

            # Format
            text = self.get_format_name(exporter)
            row.label(text=text)  # Display the user-friendly label

            # Active pre-export operation indicator icons
            if scene.move_by_collection_offset:
                row.label(text='', icon='OBJECT_ORIGIN')
            if scene.triangulate_before_export:
                row.label(text='', icon='MOD_TRIANGULATE')
            if scene.apply_transform_before_export or scene.apply_scale_before_export or scene.apply_rotation_before_export:
                row.label(text='', icon='OBJECT_DATA')
            if scene.pre_rotate_objects:
                row.label(text='', icon='DRIVER_ROTATIONAL_DIFFERENCE')

            ########## Name
            row = col_02.row(align=True)
            icon = self.get_collection_color_icon(collection)
            row.label(text=collection.name, icon=icon)

            ########## Filepath
            row = col_03.row(align=True)
            row.prop(exporter.export_properties, "filepath", text="", expand=True)
            from .shared_operator_call import call_simple_export_path_ops
            call_simple_export_path_ops(context, row, text='', outliner=False,
                                        individual_collection=True, collection_name=collection.name)

            ########## Root
            row = col_04.row(align=True)
            split_root = row.split(align=True)
            col_root = split_root.column(align=True)
            col_loc = split_root.column(align=True)

            # Root Link
            row = col_root.row(align=True)
            icon = "LINKED" if collection.use_root_object else "UNLINKED"
            row.prop(collection, "use_root_object", text='', icon=icon)
            if not collection.use_root_object:
                row.enabled = False
            row.prop(collection, "root_object", text="")

            # Loc
            row = col_loc.row(align=True)
            if collection.use_root_object:
                row.enabled = False
            row.prop(collection, "instance_offset", text="")

            # Operators
            row = col_05.row(align=True)

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

            # Add arrow button that sets the collection name and opens the menu
            arrow_op = row.operator("object.set_menu_collection", text="", icon='TRIA_DOWN')
            arrow_op.collection_name = collection.name

            # Add the Export Collection button
            op = row.operator("simple_export.export_collections", text="", icon='EXPORT')
            op.outliner = False
            op.individual_collection = True
            op.collection_name = collection.name



        else:
            row = layout.row(align=True)

            # Checkbox for selecting the collection for export
            row.prop(collection, "simple_export_selected", text="")
            visibility_properties = scene.exportlist_nPanel_properties if self.list_id == 'npanel' else scene.exportlist_scene_properties

            if 'DEFAULT' in visibility_properties.list_visibility_settings:
                icon = self.get_export_status_icon(export_path, file_exists)
                row.label(text='', icon=icon)
                # Display the collection name with the color icon
                icon = self.get_collection_color_icon(collection)
                row.label(text=collection.name, icon=icon)

            if 'FILEPATH' in visibility_properties.list_visibility_settings:
                # Display the export file path as an editable property
                row.prop(exporter.export_properties, "filepath", text="", expand=True)

                # Buttons for setting the export path and opening the directory
                # Assign Path

                from .shared_operator_call import call_simple_export_path_ops
                op = call_simple_export_path_ops(context, row, text='', outliner=False,
                                                 individual_collection=True, collection_name=collection.name)

            if 'FILENAME' in visibility_properties.list_visibility_settings:
                filename = os.path.basename(exporter.export_properties.filepath)
                row.label(text=filename)

            # Display Empty or Eyedropper button depending on the root_object state

            if 'ROOT' in visibility_properties.list_visibility_settings:
                # if collection.use_root_object:

                icon = "LINKED" if collection.use_root_object else "UNLINKED"
                row.prop(collection, "use_root_object", text='', icon=icon)

                if collection.use_root_object:
                    row.prop(collection, "root_object", text="")
                    op = row.operator("object.select_root", text="", icon='EMPTY_AXIS')
                    op.collection_name = collection.name

            if 'ORIGIN' in visibility_properties.list_visibility_settings:
                icon = "LINKED" if collection.use_root_object else "UNLINKED"
                row.prop(collection, "use_root_object", text='', icon=icon)
                row.prop(collection, "instance_offset", text="")

            if 'COLLECTION' in visibility_properties.list_visibility_settings:
                pass
            if 'FILENAME' in visibility_properties.list_visibility_settings:
                pass

            if 'FORMAT' in visibility_properties.list_visibility_settings:
                text = self.get_format_name(exporter)
                row.label(text=text)  # Display the user-friendly label

            if 'OPERATIONS' in visibility_properties.list_visibility_settings:
                if scene.move_by_collection_offset:
                    row.label(text='', icon='OBJECT_ORIGIN')
                if scene.triangulate_before_export:
                    row.label(text='', icon='MOD_TRIANGULATE')
                if scene.apply_transform_before_export or scene.apply_scale_before_export or scene.apply_rotation_before_export:
                    row.label(text='', icon='OBJECT_DATA')
                if scene.pre_rotate_objects:
                    row.label(text='', icon='DRIVER_ROTATIONAL_DIFFERENCE')

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

            # Add arrow button that sets the collection name and opens the menu
            arrow_op = row.operator("object.set_menu_collection", text="", icon='TRIA_DOWN')
            arrow_op.collection_name = collection.name

            # Add the Export Collection button
            op = row.operator("simple_export.export_collections", text="", icon='EXPORT')
            op.outliner = False
            op.individual_collection = True
            op.collection_name = collection.name

    def get_format_name(self, exporter):
        # Display the export format
        exporter_type = str(type(exporter.export_properties))
        key = ExportFormats.get_key_from_op_type(exporter_type)
        if key:
            fmt = ExportFormats.get(key)
            text = fmt.label
        else:
            text = exporter_type
        return text

    def get_export_status_icon(self, export_path, file_exists):
        is_locked = file_exists and not os.access(export_path, os.W_OK)
        # Show lock icon based on file permissions
        if is_locked:
            icon = 'LOCKED'
        elif file_exists:
            icon = 'CURRENT_FILE'
        else:
            icon = 'FILE_NEW'
        return icon

    def get_collection_color_icon(self, collection):
        # Determine the icon based on the collection's color_tag
        color_tag = collection.color_tag
        icon = COLOR_TAG_ICONS.get(color_tag, 'OUTLINER_COLLECTION')
        return icon

    def filter_items(self, context, data, propname):
        flt_flags = []
        scene = context.scene

        export_format = scene.export_format_filter
        export_format_obj = ExportFormats.get(export_format)

        for collection in bpy.data.collections:
            filter = 0
            has_exporters = len(collection.exporters) > 0

            if not scene.use_filter and has_exporters:
                filter = self.bitflag_filter_item
            elif scene.use_filter:
                exporter_types = [str(type(exporter.export_properties)) for exporter in collection.exporters]
                if any(exporter_type == export_format_obj.op_type for exporter_type in exporter_types):
                    filter = self.bitflag_filter_item

            flt_flags.append(filter)

        flt_neworder = []
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

    # UIList Properties
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
