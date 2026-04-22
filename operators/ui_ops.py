import bpy
import os

from ..functions.exporter_funcs import find_exporter
from ..functions.path_utils import clean_relative_path, export_dir_absolute, export_dir_raw


class SIMPLE_EXPORT_OT_ReloadAddon(bpy.types.Operator):
    """Reload all Simple Export scripts"""
    bl_idname = "simple_export.reload_addon"
    bl_label = "Reload Addon"
    bl_description = "Reload all Simple Export scripts"
    bl_options = {'REGISTER', 'INTERNAL'}

    def execute(self, context):
        import importlib
        import sys

        root_pkg = __package__.rsplit(".", 1)[0]

        mod_names = sorted(
            [name for name in sys.modules
             if name == root_pkg or name.startswith(root_pkg + ".")],
            key=lambda n: (-n.count("."), n),
        )

        def _do_reload():
            root_mod = sys.modules.get(root_pkg)
            if root_mod and hasattr(root_mod, "unregister"):
                try:
                    root_mod.unregister()
                except Exception as exc:
                    print(f"[Simple Export] unregister error: {exc}")

            for name in mod_names:
                mod = sys.modules.get(name)
                if mod is not None:
                    try:
                        importlib.reload(mod)
                    except Exception as exc:
                        print(f"[Simple Export] reload error for '{name}': {exc}")

            root_mod = sys.modules.get(root_pkg)
            if root_mod and hasattr(root_mod, "register"):
                try:
                    root_mod.register()
                except Exception as exc:
                    print(f"[Simple Export] register error: {exc}")

            print(f"[Simple Export] Reloaded {len(mod_names)} modules from '{root_pkg}'")

        bpy.app.timers.register(_do_reload, first_interval=0.0)
        self.report({'INFO'}, f"Queued reload of {len(mod_names)} modules…")
        return {'FINISHED'}


class SIMPLE_OT_OpenCollectionExporterProperties(bpy.types.Operator):
    """Go to the selected collection's properties and focus on the exporter"""
    bl_idname = "simple_export.open_exporter_in_properties"
    bl_label = "Open Exporter Properties"
    bl_description = "Open the properties of the selected collection and focus on the exporter settings."
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    collection_name: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        # Get the selected collection
        collection = bpy.data.collections.get(self.collection_name)
        if not collection:
            self.report({'WARNING'}, f"Collection '{self.collection_name}' not found.")
            return {'CANCELLED'}

        # Find the corresponding LayerCollection
        def find_layer_collection(layer_collection, collection):
            if layer_collection.collection == collection:
                return layer_collection
            for child in layer_collection.children:
                found = find_layer_collection(child, collection)
                if found:
                    return found
            return None

        layer_collection = find_layer_collection(context.view_layer.layer_collection, collection)
        if not layer_collection:
            self.report({'ERROR'}, f"LayerCollection for '{collection.name}' not found.")
            return {'CANCELLED'}

        # Ensure a properties editor is open and set the correct context
        for area in context.screen.areas:
            if area.type == 'PROPERTIES':
                for space in area.spaces:
                    if space.type == 'PROPERTIES':
                        space.context = 'COLLECTION'
                        context.view_layer.active_layer_collection = layer_collection
                        break
                break
        else:
            self.report({'ERROR'}, "No properties editor found. Please open one manually.")
            return {'CANCELLED'}

        self.report({'INFO'}, f"Focused on Collection: {collection.name}")
        return {'FINISHED'}


class SCENE_OT_SelectAllCollections(bpy.types.Operator):
    bl_idname = "scene.select_all_collections"
    bl_label = "Select All Collections"
    bl_description = "Select or deselect all collections for export."
    bl_options = {'REGISTER', 'UNDO'}

    deselect: bpy.props.BoolProperty(name="Invert", default=False, )

    def execute(self, context):
        for collection in bpy.data.collections:
            collection.simple_export_selected = not self.deselect
        return {'FINISHED'}


class SCENE_OT_ExpandAllCollections(bpy.types.Operator):
    bl_idname = "scene.expand_minimize_all_collections"
    bl_label = "Expand or Minimize All Collections"
    bl_description = "Expand or minimize all collections for export."
    bl_options = {'REGISTER', 'UNDO'}

    minimize: bpy.props.BoolProperty(name="Invert", default=False)
    list_id: bpy.props.StringProperty()


    def execute(self, context):
        visibility_properties = context.scene.exportlist_nPanel_properties
        visibility_properties.list_visibility_settings = {'FILEPATH', 'ORIGIN', 'PRESET', 'OPERATIONS'} if not self.minimize else set()
        return {'FINISHED'}


class SCENE_OT_OpenExportDirectory(bpy.types.Operator):
    """
    Operator to open the export directory of the currently selected collection in the file explorer.
    """
    bl_idname = "scene.open_export_directory"
    bl_label = "Open Export Directory"
    bl_description = "Open the export directory of the currently selected collection in the file explorer."
    bl_options = {'REGISTER', 'UNDO', 'PRESET'}

    collection_name: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if not collection or len(collection.exporters) == 0:
            self.report({'WARNING'}, "No valid exporter found for the active collection.")
            return {'CANCELLED'}

        scene = context.scene
        exporter = find_exporter(collection, format_filter=scene.export_format)
        export_path = exporter.export_properties.filepath
        export_dir = os.path.dirname(export_path)
        export_dir = clean_relative_path(os.path.dirname(export_dir))

        if not os.path.exists(export_dir):
            self.report({'WARNING'}, f"Directory does not exist: {export_dir}")
            return {'CANCELLED'}

        bpy.ops.wm.path_open(filepath=export_dir)
        self.report({'INFO'}, f"Opened directory: {export_dir}")
        return {'FINISHED'}


class SIMPLE_EXPORT_OT_ClearFilters(bpy.types.Operator):
    """Reset all Export Target filters"""
    bl_idname = "simple_export.clear_filters"
    bl_label = "Clear Filters"
    bl_description = "Reset all Export Target filters to show all collections"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        scene.filter_format = 'ALL'
        scene.filter_color_tag = 'ALL'
        scene.filter_selected_only = False
        scene.filter_name = ""
        scene.filter_file_status = 'ALL'
        scene.filter_directory = 'ALL'
        scene.filter_preset_addon_preset = 'ALL'
        scene.filter_preset_export_preset = 'ALL'
        scene.filter_custom_group = 'ALL'
        return {'FINISHED'}


class SIMPLE_EXPORT_OT_AssignCollectionGroup(bpy.types.Operator):
    """Assign an existing group name to the collection"""
    bl_idname = "simple_export.assign_collection_group"
    bl_label = "Assign Group"
    bl_options = {'REGISTER', 'UNDO'}

    group_name: bpy.props.StringProperty(options={'HIDDEN'})
    collection_name: bpy.props.StringProperty(options={'HIDDEN'})

    def execute(self, context):
        collection = bpy.data.collections.get(self.collection_name)
        if not collection:
            self.report({'WARNING'}, f"Collection '{self.collection_name}' not found.")
            return {'CANCELLED'}
        collection.export_group_name = self.group_name
        return {'FINISHED'}


class SIMPLE_EXPORT_OT_AddNewCollectionGroup(bpy.types.Operator):
    """Create a new group name and assign it to a collection"""
    bl_idname = "simple_export.add_new_collection_group"
    bl_label = "Add New Group"
    bl_options = {'REGISTER', 'UNDO'}

    group_name: bpy.props.StringProperty(name="Group Name", default="")
    collection_name: bpy.props.StringProperty(options={'HIDDEN'}, default="")
    update_filter: bpy.props.BoolProperty(options={'HIDDEN'}, default=False)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        self.layout.prop(self, "group_name")

    def execute(self, context):
        if not self.group_name.strip():
            self.report({'WARNING'}, "Group name cannot be empty.")
            return {'CANCELLED'}

        scene = context.scene
        collection = None

        if self.collection_name:
            collection = bpy.data.collections.get(self.collection_name)
        elif 0 <= scene.collection_index < len(bpy.data.collections):
            collection = bpy.data.collections[scene.collection_index]

        if not collection:
            self.report({'WARNING'}, "No collection selected to assign the group to.")
            return {'CANCELLED'}

        name = self.group_name.strip()
        collection.export_group_name = name

        if self.update_filter:
            if not collection.exporters:
                self.report({'WARNING'}, f"Group '{name}' created, but '{collection.name}' has no exporter — filter not set.")
            else:
                scene.filter_custom_group = name

        self.report({'INFO'}, f"Group '{name}' assigned to '{collection.name}'.")
        return {'FINISHED'}


class SIMPLE_EXPORT_OT_SetFilterGroup(bpy.types.Operator):
    """Set the User Group filter"""
    bl_idname = "simple_export.set_filter_group"
    bl_label = "Filter by Group"
    bl_options = {'REGISTER', 'UNDO'}

    group_name: bpy.props.StringProperty(options={'HIDDEN'}, default='ALL')

    def execute(self, context):
        context.scene.filter_custom_group = self.group_name
        return {'FINISHED'}


class SIMPLE_EXPORT_MT_FilterGroupMenu(bpy.types.Menu):
    """Filter collections by user group"""
    bl_label = "User Group"
    bl_idname = "SIMPLE_EXPORT_MT_FilterGroupMenu"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        op = layout.operator("simple_export.set_filter_group", text="All User Groups")
        op.group_name = 'ALL'

        op = layout.operator("simple_export.set_filter_group", text="No User Groups", icon='X')
        op.group_name = 'NONE'

        layout.separator()

        groups = sorted({
            col.export_group_name
            for col in bpy.data.collections
            if getattr(col, 'export_group_name', '') and col.exporters
        })

        if groups:
            for group in groups:
                op = layout.operator("simple_export.set_filter_group", text=group)
                op.group_name = group
            layout.separator()

        op = layout.operator("simple_export.add_new_collection_group", text="Add New Group...", icon='ADD')
        op.collection_name = ""
        op.update_filter = True


class SIMPLE_EXPORT_MT_CollectionGroupMenu(bpy.types.Menu):
    """Pick or clear the user group for a collection.
    Resolves via menu_collection_name when set, otherwise falls back to collection_index."""
    bl_label = "User Group"
    bl_idname = "SIMPLE_EXPORT_MT_CollectionGroupMenu"

    def draw(self, context):
        layout = self.layout
        scene = context.scene

        menu_name = getattr(scene, 'menu_collection_name', '')
        if menu_name:
            collection = bpy.data.collections.get(menu_name)
        elif 0 <= scene.collection_index < len(bpy.data.collections):
            collection = bpy.data.collections[scene.collection_index]
        else:
            collection = None

        if not collection:
            layout.label(text="No collection selected", icon='INFO')
            return

        op = layout.operator("simple_export.assign_collection_group", text="None", icon='X')
        op.group_name = ""
        op.collection_name = collection.name

        layout.separator()

        groups = sorted({
            col.export_group_name
            for col in bpy.data.collections
            if getattr(col, 'export_group_name', '')
        })

        if groups:
            for group in groups:
                op = layout.operator("simple_export.assign_collection_group", text=group)
                op.group_name = group
                op.collection_name = collection.name
            layout.separator()

        op = layout.operator("simple_export.add_new_collection_group", text="Add New Group...", icon='ADD')
        op.collection_name = collection.name


class SIMPLE_EXPORT_OT_SetFilterDirectory(bpy.types.Operator):
    """Set the Directory filter"""
    bl_idname = "simple_export.set_filter_directory"
    bl_label = "Filter by Directory"
    bl_options = {'REGISTER', 'UNDO'}

    directory: bpy.props.StringProperty(options={'HIDDEN'}, default='ALL')

    def execute(self, context):
        context.scene.filter_directory = self.directory
        return {'FINISHED'}


class SIMPLE_EXPORT_MT_FilterDirectoryMenu(bpy.types.Menu):
    """Filter collections by output directory"""
    bl_label = "Directory"
    bl_idname = "SIMPLE_EXPORT_MT_FilterDirectoryMenu"

    def draw(self, context):
        layout = self.layout

        op = layout.operator("simple_export.set_filter_directory", text="All Directories")
        op.directory = 'ALL'

        op = layout.operator("simple_export.set_filter_directory", text="No Directory", icon='X')
        op.directory = 'NO_PATH'

        layout.separator()

        dirs = {}
        for col in bpy.data.collections:
            if col.exporters:
                try:
                    exp = find_exporter(col)
                    if exp is None:
                        continue
                    raw = exp.export_properties.filepath
                    abs_d = export_dir_absolute(raw)
                    if abs_d and abs_d not in dirs:
                        dirs[abs_d] = export_dir_raw(raw)
                except Exception:
                    pass

        for abs_d in sorted(dirs):
            raw_d = dirs[abs_d]
            op = layout.operator("simple_export.set_filter_directory",
                                 text=raw_d or abs_d)
            op.directory = raw_d or abs_d


class SIMPLE_EXPORT_OT_EditPreExportOps(bpy.types.Operator):
    """Edit pre-export operations for a collection"""
    bl_idname = "simple_export.edit_pre_export_ops"
    bl_label = "Pre-Export Operations"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty(options={'HIDDEN'})

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=250)

    def draw(self, context):
        layout = self.layout
        collection = bpy.data.collections.get(self.collection_name)
        if not collection or not hasattr(collection, 'pre_export_ops'):
            layout.label(text="Collection not found", icon='ERROR')
            return
        col = layout.column(align=True)
        col.prop(collection.pre_export_ops, 'move_by_collection_offset')
        col.prop(collection.pre_export_ops, 'triangulate_before_export')

    def execute(self, context):
        return {'FINISHED'}


class SIMPLE_EXPORT_OT_BatchAssignPreExportOps(bpy.types.Operator):
    """Assign pre-export operations to all selected collections"""
    bl_idname = "simple_export.batch_assign_pre_export_ops"
    bl_label = "Batch Assign Pre-Export Operations"
    bl_description = "Set pre-export operations for all selected collections"
    bl_options = {'REGISTER', 'UNDO'}

    move_by_collection_offset: bpy.props.BoolProperty(
        name="Move to Origin",
        description="Move collection objects to the world origin before exporting",
        default=False,
    )
    triangulate_before_export: bpy.props.BoolProperty(
        name="Triangulate Meshes",
        description="Add a triangulate modifier before exporting",
        default=False,
    )

    def invoke(self, context, event):
        # Pre-fill from the first selected collection
        for col in bpy.data.collections:
            if getattr(col, 'simple_export_selected', False) and hasattr(col, 'pre_export_ops'):
                self.move_by_collection_offset = col.pre_export_ops.move_by_collection_offset
                self.triangulate_before_export = col.pre_export_ops.triangulate_before_export
                break

        wm = context.window_manager
        if context.area is not None:
            return wm.invoke_props_dialog(self, width=300)
        for window in wm.windows:
            for area in window.screen.areas:
                for region in area.regions:
                    if region.type == 'WINDOW':
                        with context.temp_override(window=window, area=area, region=region):
                            return wm.invoke_props_dialog(self, width=300)
        return wm.invoke_props_dialog(self, width=300)

    def draw(self, context):
        layout = self.layout
        selected = [c for c in bpy.data.collections if getattr(c, 'simple_export_selected', False)]
        count = len(selected)
        col = layout.column(align=True)
        col.label(text=f"Apply to {count} selected collection{'s' if count != 1 else ''}:", icon='INFO')
        col.separator(factor=0.5)
        col.prop(self, 'move_by_collection_offset')
        col.prop(self, 'triangulate_before_export')

    def execute(self, context):
        selected = [c for c in bpy.data.collections if getattr(c, 'simple_export_selected', False)]
        if not selected:
            self.report({'WARNING'}, "No selected collections found.")
            return {'CANCELLED'}

        updated = 0
        for collection in selected:
            if not hasattr(collection, 'pre_export_ops'):
                continue
            collection.pre_export_ops.move_by_collection_offset = self.move_by_collection_offset
            collection.pre_export_ops.triangulate_before_export = self.triangulate_before_export
            updated += 1

        self.report({'INFO'}, f"Pre-export operations updated for {updated} collection{'s' if updated != 1 else ''}.")
        return {'FINISHED'}


classes = (
    SCENE_OT_SelectAllCollections,
    SCENE_OT_ExpandAllCollections,
    SCENE_OT_OpenExportDirectory,
    SIMPLE_OT_OpenCollectionExporterProperties,
    SIMPLE_EXPORT_OT_ReloadAddon,
    SIMPLE_EXPORT_OT_ClearFilters,
    SIMPLE_EXPORT_OT_AssignCollectionGroup,
    SIMPLE_EXPORT_OT_AddNewCollectionGroup,
    SIMPLE_EXPORT_OT_SetFilterGroup,
    SIMPLE_EXPORT_MT_CollectionGroupMenu,
    SIMPLE_EXPORT_MT_FilterGroupMenu,
    SIMPLE_EXPORT_OT_SetFilterDirectory,
    SIMPLE_EXPORT_MT_FilterDirectoryMenu,
    SIMPLE_EXPORT_OT_EditPreExportOps,
    SIMPLE_EXPORT_OT_BatchAssignPreExportOps,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
