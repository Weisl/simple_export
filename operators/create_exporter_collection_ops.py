import os

import bpy

from .shared_properties import (
    SharedPathProps, SharedFilenameProps,
    SharedPathAssignmentProps, SharedPresetAssignmentProps, CollectionNamingProps,
    CollectionOriginProps, CollectionSettingsProps, SharedFormatProps
)
from ..core.export_path_func import assign_exporter_path
from ..core.export_path_func import generate_base_name
from ..functions.collections_setup import setup_collection_properties
from ..functions.exporter_funcs import get_all_children_and_descendants
from ..functions.preset_func import assign_preset
from ..ui.shared_draw import draw_export_folderpath_properties


def get_addon_preset_items(self, context):
    from ..presets_addon.exporter_preset import simple_export_presets_folder
    folder = simple_export_presets_folder()
    items = []
    if os.path.isdir(folder):
        for fname in sorted(os.listdir(folder)):
            if fname.endswith('.py'):
                name = os.path.splitext(fname)[0]
                items.append((name, name, ""))
    return items if items else [('NONE', "No Presets Available", "")]



def determine_parent_collection(context, parent_collection_name="", top_object=None):
    """Determine the parent collection based on the specified hierarchy."""
    if parent_collection_name in bpy.data.collections:
        parent_collection_name = bpy.data.collections.get(parent_collection_name, None)
        if parent_collection_name:
            return parent_collection_name
    if parent_collection_name:
        from ..functions.collections_setup import create_collection
        return create_collection(parent_collection_name)
    if top_object and top_object.users_collection:
        return top_object.users_collection[0]
    return context.scene.collection


class EXPORT_OT_CreateExportCollections(
    SharedFormatProps,
    SharedPathAssignmentProps,
    SharedPresetAssignmentProps,
    CollectionNamingProps,
    CollectionOriginProps,
    CollectionSettingsProps,
    SharedPathProps,
    SharedFilenameProps,
    bpy.types.Operator
):
    """Create a new collection for each selected object and its children, preserving hierarchy."""
    bl_idname = "simple_export.create_export_collections"
    bl_label = "Create Export Collections"
    bl_description = "Create Export Collections for selected objects and their children, preserving hierarchy."
    bl_options = {'REGISTER', 'UNDO'}
    # TODO: Add support for adding exporters without selected objects

    addon_preset_selection: bpy.props.EnumProperty(
        name="Preset",
        description="Simple Export addon preset to use for this collection",
        items=get_addon_preset_items,
    )

    applied_preset_tracker: bpy.props.StringProperty(options={'HIDDEN', 'SKIP_SAVE'})

    existing_exporter_action: bpy.props.EnumProperty(
        name="Existing Exporter",
        description="How to handle exporters already assigned to collections that already exist",
        items=[
            ('REPLACE', "Replace", "Remove existing exporters and replace them with a new one"),
            ('ADD', "Add New", "Keep existing exporters and add a new one alongside them"),
            ('CANCEL', "Cancel", "Skip collections that already have an exporter assigned"),
        ],
        default='ADD'
    )

    warn_existing_exporters: bpy.props.BoolProperty(
        default=False,
        options={'HIDDEN', 'SKIP_SAVE'}
    )

    use_numbering: bpy.props.BoolProperty(
        name="Use Numbering",
        description="Add numbered suffix to collection names",
        default=False
    )

    # Properties whose current value should not be overwritten when switching presets
    # inside the operator dialog — the user sets these explicitly.
    _PRESET_SKIP_PROPS = {'set_export_path'}

    def _apply_addon_preset_to_self(self, preset_path):
        """Parse an addon preset file and apply its scene.* values to operator properties."""
        if not os.path.isfile(preset_path):
            return
        with open(preset_path, 'r') as f:
            for line in f:
                line = line.strip()
                if not line.startswith('scene.'):
                    continue
                try:
                    prop_part = line[6:]  # strip 'scene.'
                    prop_name, value_str = prop_part.split(' = ', 1)
                    if prop_name in self._PRESET_SKIP_PROPS:
                        continue
                    if hasattr(self, prop_name):
                        setattr(self, prop_name, eval(value_str))
                except Exception:
                    pass

    def check(self, context):
        if self.addon_preset_selection == self.applied_preset_tracker:
            return False
        self.applied_preset_tracker = self.addon_preset_selection
        if self.addon_preset_selection and self.addon_preset_selection != 'NONE':
            from ..presets_addon.exporter_preset import simple_export_presets_folder
            preset_path = os.path.join(
                simple_export_presets_folder(),
                self.addon_preset_selection + '.py'
            )
            self._apply_addon_preset_to_self(preset_path)
        return True

    def invoke(self, context, event):
        self.applied_preset_tracker = ""

        # Pre-populate set_export_path from the scene so that the preset's saved
        # value is visible in the dialog.  The preset applies its settings to the
        # scene, so context.scene.set_export_path reflects the preset's intent.
        # Because set_export_path is in _PRESET_SKIP_PROPS it will NOT be
        # overwritten again when check() fires below.
        scene = context.scene
        if hasattr(scene, 'set_export_path'):
            self.set_export_path = scene.set_export_path

        selected = context.scene.simple_export_selected_preset
        if selected:
            name = os.path.splitext(os.path.basename(selected))[0]
            try:
                self.addon_preset_selection = name
            except Exception:
                pass

        # Check whether any selected object already lives in a collection with an exporter
        self.warn_existing_exporters = any(
            col.exporters
            for obj in context.selected_objects
            for col in obj.users_collection
        )

        return context.window_manager.invoke_props_dialog(self, width=400)

    def execute(self, context):
        """Execute the operator to create export collections."""
        selected_objects = context.selected_objects
        if not selected_objects:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}

        top_objects = [top_object for top_object in selected_objects if
                       not top_object.parent or top_object.parent not in selected_objects]

        # Snapshot each top object's current exporter-bearing collections BEFORE any collection
        # creation or object relinking happens. This is needed so that REPLACE can remove exporters
        # from the original collections even when the target collection has a different name.
        from ..functions.exporter_funcs import create_collection_exporter, remove_all_collection_exporters
        original_exporter_cols = {}
        if self.warn_existing_exporters:
            for obj in top_objects:
                cols = [col for col in obj.users_collection if col.exporters]
                if cols:
                    original_exporter_cols[obj.name] = cols

        if not self.collection_naming_overwrite or not self.collection_name_new:
            exporter_collections = self.create_individual_collections(context, top_objects)
        else:
            if self.use_numbering:
                exporter_collections = self.create_numbered_collections(context, top_objects)
            else:
                exporter_collections = self.create_single_collection(context, top_objects)

        for export_data in exporter_collections:
            if isinstance(export_data, tuple):
                export_collection, top_object = export_data
            else:
                export_collection = export_data
                top_object = None

            if export_collection is not None:
                export_collection = setup_collection_properties(self, export_collection, top_object)

                has_exporters = bool(export_collection.exporters)
                orig_cols = original_exporter_cols.get(top_object.name, []) if top_object else []

                if has_exporters or orig_cols:
                    if self.existing_exporter_action == 'CANCEL':
                        self.report({'INFO'}, f"Skipped '{export_collection.name}': already has an exporter assigned.")
                        continue
                    elif self.existing_exporter_action == 'REPLACE':
                        # Remove from the target collection if it already has exporters
                        if has_exporters:
                            remove_all_collection_exporters(export_collection)
                        # Also remove from the original collections (covers the case where the
                        # target collection was freshly created and has a different name)
                        for orig_col in orig_cols:
                            if orig_col != export_collection:
                                remove_all_collection_exporters(orig_col)

                exporter = create_collection_exporter(self, context, export_collection)

                self.report({'INFO'},
                            f"Export collection '{export_collection.name}' created successfully for all objects.")

                # Set preset
                if self.assign_preset:
                    from ..presets_export.preset_format_functions import get_format_preset_filepath
                    preset_file = get_format_preset_filepath(self, self.export_format)
                    assign_preset(exporter, preset_file)
                    export_collection.simple_export_export_preset = os.path.splitext(os.path.basename(preset_file))[0]

                selected_addon_preset = context.scene.simple_export_selected_preset
                if selected_addon_preset:
                    export_collection.simple_export_addon_preset = self.addon_preset_selection

                if self.set_export_path and exporter and hasattr(exporter, 'export_properties'):
                    assign_exporter_path(self, export_collection.name, exporter)
            else:
                self.report({'ERROR'}, "Failed to create export collection.")

        return {'FINISHED'}

    def create_individual_collections(self, context, top_objects):
        """Create individual collections for each selected object."""
        exporter_collections = []
        for top_object in top_objects:
            collection_name = generate_base_name(
                top_object.name,
                getattr(self, 'collection_prefix', ''),
                getattr(self, 'collection_suffix', ''),
                getattr(self, 'collection_blend_prefix', '')
            )
            if collection_name in bpy.data.collections:
                export_collection = bpy.data.collections[collection_name]
                self.report({'WARNING'}, f"Collection '{collection_name}' already exists. Using existing collection.")
                self._link_objects_to_collection(top_object, export_collection)
            else:
                export_collection = self.create_and_setup_collection(context, collection_name, top_object)
            exporter_collections.append((export_collection, top_object))
        return exporter_collections

    def create_numbered_collections(self, context, top_objects):
        """Create numbered collections for each selected object."""
        exporter_collections = []
        for index, top_object in enumerate(top_objects):
            padded_index = f"{index:03}"
            collection_name = f"{self.collection_name_new}_{padded_index}"
            if collection_name in bpy.data.collections:
                export_collection = bpy.data.collections[collection_name]
                self.report({'WARNING'}, f"Collection '{collection_name}' already exists. Using existing collection.")
                self._link_objects_to_collection(top_object, export_collection)
            else:
                export_collection = self.create_and_setup_collection(context, collection_name, top_object)
            exporter_collections.append((export_collection, top_object))
        return exporter_collections

    def _link_objects_to_collection(self, top_object, export_collection):
        """Link top_object and its hierarchy into export_collection, moving them out of other collections."""
        hierarchy_objects = get_all_children_and_descendants(top_object, include_top=True)
        for obj in hierarchy_objects:
            if export_collection not in obj.users_collection:
                export_collection.objects.link(obj)
            for col in obj.users_collection:
                if col != export_collection:
                    col.objects.unlink(obj)

    def create_single_collection(self, context, top_objects):
        """Create a single collection for all selected objects."""
        exporter_collections = []
        collection_name = self.collection_name_new
        if collection_name in bpy.data.collections:
            export_collection = bpy.data.collections[collection_name]
            self.report({'WARNING'}, f"Collection '{collection_name}' already exists. Using existing collection.")
        else:
            export_collection = bpy.data.collections.new(collection_name)
            parent_collection = determine_parent_collection(context, self.parent_collection, None)
            parent_collection.children.link(export_collection)

        for top_object in top_objects:
            # objects = context.selected_objects if self.only_selection else bpy.data.objects
            objects = bpy.data.objects

            hierarchy_objects = get_all_children_and_descendants(top_object)
            for obj in hierarchy_objects:
                if export_collection not in obj.users_collection:
                    export_collection.objects.link(obj)
                for col in obj.users_collection:
                    if col != export_collection:
                        col.objects.unlink(obj)

        if export_collection:
            exporter_collections.append((export_collection, top_object))
        return exporter_collections

    def create_and_setup_collection(self, context, collection_name, top_object):
        """Create a new collection and set it up with the given name and objects."""
        export_collection = bpy.data.collections.new(collection_name)
        parent_collection = determine_parent_collection(context, self.parent_collection, top_object)
        if parent_collection:
            parent_collection.children.link(export_collection)
        else:
            self.report({'ERROR'}, "Failed to determine parent collection.")
            return None

        # objects = context.selected_objects if self.only_selection else bpy.data.objects
        # hierarchy_objects = get_all_children_and_descendants(top_object, objects)
        hierarchy_objects = get_all_children_and_descendants(top_object, include_top=True)
        # Link all hierarchy objects to the new collection

        for obj in hierarchy_objects:
            if export_collection not in obj.users_collection:
                export_collection.objects.link(obj)
            for col in obj.users_collection:
                if col != export_collection:
                    col.objects.unlink(obj)

        return export_collection

    def draw(self, context):
        from .. import __package__ as base_package
        layout = self.layout

        layout.prop(self, "addon_preset_selection", text="")
        op = layout.operator("preferences.addon_show", text="New Preset", icon='PREFERENCES')
        op.module = base_package

        layout.separator()
        layout.prop(self, "set_export_path")
        if self.set_export_path:
            from ..ui.shared_draw import draw_export_folderpath_properties
            draw_export_folderpath_properties(layout, self)

        layout.separator()
        layout.prop(self, "create_empty_root")
        if self.create_empty_root:
            prefs = context.preferences.addons[base_package].preferences
            col = layout.column(align=True)
            col.use_property_split = True
            col.prop(prefs, "root_empty_display_type", text="Shape")
            col.prop(prefs, "root_empty_display_size", text="Size")

        if self.warn_existing_exporters:
            layout.separator()
            box = layout.box()
            col = box.column(align=True)
            col.label(text="Selected object(s) are already in a collection", icon='ERROR')
            col.label(text="with an exporter assigned.")
            col.separator()
            col.label(text="How would you like to proceed?")
            col.prop(self, "existing_exporter_action", expand=True)



classes = (
    EXPORT_OT_CreateExportCollections,
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
