import os

import bpy

from ..core.export_formats import ExportFormats
from ..core.info import COLOR_TAG_ICONS
from ..functions.exporter_funcs import find_exporter
from ..functions.path_utils import clean_relative_path
from ..functions.preset_func import collection_has_preset_changes


def collection_passes_uilist_filters(collection, scene):
    """Return True if collection passes all active UIList filters."""
    if not collection.exporters:
        return False

    exporter = find_exporter(collection)
    export_path = clean_relative_path(exporter.export_properties.filepath)
    file_exists = os.path.exists(export_path)
    is_locked = file_exists and not os.access(export_path, os.W_OK)

    # Format filter
    if scene.filter_format != 'ALL':
        export_format_obj = ExportFormats.get(scene.filter_format)
        exporter_types = [str(type(e.export_properties)) for e in collection.exporters]
        if not any(t == export_format_obj.op_type for t in exporter_types):
            return False

    # Color tag
    if scene.filter_color_tag != 'ALL':
        if collection.color_tag != scene.filter_color_tag:
            return False

    # Selected only
    if scene.filter_selected_only:
        if not collection.simple_export_selected:
            return False

    # Name search
    if scene.filter_name:
        if scene.filter_name.lower() not in collection.name.lower():
            return False

    # File status
    if scene.filter_file_status != 'ALL':
        if scene.filter_file_status == 'NEW' and file_exists:
            return False
        elif scene.filter_file_status == 'EXISTS' and not file_exists:
            return False
        elif scene.filter_file_status == 'LOCKED' and not is_locked:
            return False
        elif scene.filter_file_status == 'FAILED' and not getattr(collection, 'last_export_failed', False):
            return False

    # Directory
    if scene.filter_directory != 'ALL':
        dir_path = os.path.dirname(export_path)
        if scene.filter_directory != dir_path:
            return False

    # Export format preset
    if scene.filter_preset_addon_preset != 'ALL':
        if scene.filter_preset_addon_preset != getattr(collection, 'simple_export_addon_preset', ''):
            return False

    # Addon preset — matches the displayed value: format preset with fallback to addon preset
    if scene.filter_preset_export_preset != 'ALL':
        if scene.filter_preset_export_preset != getattr(collection, 'simple_export_export_preset', ''):
            return False

    # Custom group filter
    if scene.filter_custom_group == 'NONE':
        if getattr(collection, 'export_group_name', ''):
            return False
    elif scene.filter_custom_group != 'ALL':
        if getattr(collection, 'export_group_name', '') != scene.filter_custom_group:
            return False

    return True


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
        op = layout.operator("object.create_root_empty", text="Create Root Empty", icon='EMPTY_AXIS')
        op.collection_name = collection_name

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
        scene = context.scene
        row = layout.row(align=True)
        row.label(text="Sort:")
        row.prop(scene, "sort_mode", text="")
        icon = 'SORT_DESC' if scene.sort_reverse else 'SORT_ASC'
        row.prop(scene, "sort_reverse", text="", icon=icon, toggle=True)

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
        format_filter = scene.filter_format if scene.filter_format != 'ALL' else None
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
            icon = self.get_export_status_icon(export_path, file_exists, collection)
            row.label(text='', icon=icon)

            # Format
            text = self.get_format_name(exporter)
            row.label(text=text)  # Display the user-friendly label

            # Active pre-export operation indicator icons (per-collection)
            col_ops = collection.pre_export_ops
            if col_ops.move_by_collection_offset:
                row.label(text='', icon='OBJECT_ORIGIN')
            if col_ops.triangulate_before_export:
                row.label(text='', icon='MOD_TRIANGULATE')
            if col_ops.apply_transform_before_export or col_ops.apply_scale_before_export or col_ops.apply_rotation_before_export:
                row.label(text='', icon='OBJECT_DATA')
            if col_ops.pre_rotate_objects:
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
            col = layout.column(align=True)
            row = col.row(align=True)

            # Checkbox for selecting the collection for export
            row.prop(collection, "simple_export_selected", text="")
            visibility_properties = scene.exportlist_nPanel_properties if self.list_id == 'npanel' else scene.exportlist_scene_properties


            icon = self.get_export_status_icon(export_path, file_exists, collection)
            row.label(text='', icon=icon)
            # Display the collection name with the color icon
            icon = self.get_collection_color_icon(collection)
            row.prop(collection, 'name',text='',icon=icon)

            # Add arrow button that sets the collection name and opens the menu
            arrow_op = row.operator("object.set_menu_collection", text="", icon='TRIA_DOWN')
            arrow_op.collection_name = collection.name

            # Add the Export Collection button
            op = row.operator("simple_export.export_collections", text="", icon='EXPORT')
            op.outliner = False
            op.individual_collection = True
            op.collection_name = collection.name

            if 'PRESET' in visibility_properties.list_visibility_settings:
                row = col.row(align=True)
                export_preset = getattr(collection, 'simple_export_export_preset', '')
                addon_preset = getattr(collection, 'simple_export_addon_preset', '')
                addon_preset_text = addon_preset or '-'
                export_preset_text = export_preset or '-'
                if addon_preset_text != '-' and collection_has_preset_changes(collection, exporter, scene):
                    addon_preset_text += ' *'
                if export_preset_text != '-' and collection_has_preset_changes(collection, exporter, scene):
                    export_preset_text += ' *'
                row.label(text=addon_preset_text)
                row.label(text=export_preset_text)


            if 'FILEPATH' in visibility_properties.list_visibility_settings:
                row = col.row(align=True)
                # Display the export file path as an editable property
                row.prop(exporter.export_properties, "filepath", text="", expand=True)

                # Buttons for setting the export path and opening the directory
                # Assign Path

                from .shared_operator_call import call_simple_export_path_ops
                op = call_simple_export_path_ops(context, row, text='', outliner=False,
                                                 individual_collection=True, collection_name=collection.name)


            # Display Empty or Eyedropper button depending on the root_object state
            if 'ORIGIN' in visibility_properties.list_visibility_settings:
                row = col.row(align=True)
                icon = "LINKED" if collection.use_root_object else "UNLINKED"
                row.prop(collection, "use_root_object", text='', icon=icon)
    
                row.enabled = False if collection.use_root_object else True
                row.prop(collection, "instance_offset", text="")
                    
                row.prop(collection, "root_object", text="")
                op = row.operator("object.select_root", text="", icon='EMPTY_AXIS')
                op.collection_name = collection.name

            if 'COLLECTION' in visibility_properties.list_visibility_settings:
                row = col.row(align=True)
                pass


            if 'OPERATIONS' in visibility_properties.list_visibility_settings:
                col_ops = collection.pre_export_ops
                if col_ops.move_by_collection_offset:
                    row.label(text='', icon='OBJECT_ORIGIN')
                if col_ops.triangulate_before_export:
                    row.label(text='', icon='MOD_TRIANGULATE')
                if col_ops.apply_transform_before_export or col_ops.apply_scale_before_export or col_ops.apply_rotation_before_export:
                    row.label(text='', icon='OBJECT_DATA')
                if col_ops.pre_rotate_objects:
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

            col.separator()


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

    def get_export_status_icon(self, export_path, file_exists, collection=None):
        is_locked = file_exists and not os.access(export_path, os.W_OK)
        if collection and getattr(collection, 'last_export_failed', False):
            return 'ERROR'
        if is_locked:
            return 'LOCKED'
        elif file_exists:
            return 'CURRENT_FILE'
        else:
            return 'FILE_NEW'

    def get_collection_color_icon(self, collection):
        # Determine the icon based on the collection's color_tag
        color_tag = collection.color_tag
        icon = COLOR_TAG_ICONS.get(color_tag, 'OUTLINER_COLLECTION')
        return icon

    def filter_items(self, context, data, propname):
        scene = context.scene
        flt_flags = [
            self.bitflag_filter_item if collection_passes_uilist_filters(col, scene) else 0
            for col in bpy.data.collections
        ]

        # Sorting
        flt_neworder = []
        if scene.sort_mode != 'NONE':
            indexed = list(enumerate(bpy.data.collections))
            rev = scene.sort_reverse

            if scene.sort_mode == 'NAME':
                sorted_pairs = sorted(indexed, key=lambda x: x[1].name.lower(), reverse=rev)
            elif scene.sort_mode == 'FORMAT':
                def format_key(pair):
                    c = pair[1]
                    if not c.exporters:
                        return ''
                    exp = find_exporter(c)
                    return ExportFormats.get_key_from_op_type(str(type(exp.export_properties))) or ''
                sorted_pairs = sorted(indexed, key=format_key, reverse=rev)
            elif scene.sort_mode == 'SELECTED_FIRST':
                sorted_pairs = sorted(indexed, key=lambda x: (0 if x[1].simple_export_selected else 1, x[1].name.lower()), reverse=rev)
            elif scene.sort_mode == 'COLOR_TAG':
                sorted_pairs = sorted(indexed, key=lambda x: x[1].color_tag, reverse=rev)
            elif scene.sort_mode == 'PRESET':
                sorted_pairs = sorted(indexed, key=lambda x: getattr(x[1], 'simple_export_export_preset', '').lower(), reverse=rev)
            else:
                sorted_pairs = indexed

            flt_neworder = [orig_idx for orig_idx, _ in sorted_pairs]

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
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)

    # Remove Scene properties
    del bpy.types.Scene.menu_collection_name
