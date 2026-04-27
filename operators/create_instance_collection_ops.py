import bpy
from mathutils import Vector

from .collection_offset_ops import create_root_empty_for_collection
from ..functions.exporter_funcs import get_all_children_and_descendants
from ..functions.collection_layer import set_active_layer_Collection
from .create_exporter_collection_ops import determine_parent_collection


def _move_objects_to_collection(objects, collection):
    """Link objects to collection and unlink them from all other collections."""
    for obj in objects:
        current_collections = [c for c in obj.users_collection if c != collection]
        collection.objects.link(obj)
        for col in current_collections:
            col.objects.unlink(obj)


class OBJECT_OT_CreateInstanceCollection(bpy.types.Operator):
    """Group selected objects into a new collection with a root empty, ready for instancing."""
    bl_idname = "simple_export.create_instance_collection"
    bl_label = "Create Instance Collection"
    bl_description = "Create a collection from the selection with a root empty for use as a Collection Instance"
    bl_options = {'REGISTER', 'UNDO'}

    collection_name: bpy.props.StringProperty(
        name="Name",
        default="",
    )
    selection_mode: bpy.props.EnumProperty(
        name="Selection Mode",
        items=[
            ('BY_HIERARCHY', "By Hierarchy", "One collection per top-level selected object; children included"),
            ('SINGLE', "Single", "All selected objects into one collection"),
        ],
        default='BY_HIERARCHY',
    )
    root_empty_suffix: bpy.props.StringProperty(
        name="Root Empty Suffix",
        default="_root",
    )
    mark_as_asset: bpy.props.BoolProperty(
        name="Mark as Asset",
        description="Mark the new collection as a Blender asset so it appears in the Asset Browser",
        default=False,
    )

    def invoke(self, context, event):
        if context.active_object:
            self.collection_name = context.active_object.name
        return context.window_manager.invoke_props_dialog(self, width=350)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "selection_mode", expand=True)
        layout.separator()
        if self.selection_mode == 'SINGLE':
            row = layout.row()
            row.alert = not self.collection_name
            row.prop(self, "collection_name", text="Collection Name")
        layout.prop(self, "root_empty_suffix")
        layout.separator()
        layout.prop(self, "mark_as_asset")

    def execute(self, context):
        from .. import __package__ as base_package
        prefs = context.preferences.addons[base_package].preferences

        selected = context.selected_objects
        if not selected:
            self.report({'WARNING'}, "No objects selected.")
            return {'CANCELLED'}

        if self.selection_mode == 'SINGLE' and not self.collection_name:
            self.report({'ERROR'}, "Collection name is required for Single mode.")
            return {'CANCELLED'}

        top_objects = [o for o in selected if o.parent is None or o.parent not in selected]

        if self.selection_mode == 'SINGLE':
            self._create_single(context, top_objects, selected, prefs)
        else:
            for top_obj in top_objects:
                self._create_for_hierarchy(context, top_obj, prefs)

        return {'FINISHED'}

    def _create_single(self, context, top_objects, all_selected, prefs):
        collection = bpy.data.collections.new(self.collection_name)
        parent = determine_parent_collection(context, top_object=top_objects[0])
        parent.children.link(collection)
        set_active_layer_Collection(collection.name)

        all_objects = []
        for top_obj in top_objects:
            all_objects.extend(get_all_children_and_descendants(top_obj, include_top=True))

        _move_objects_to_collection(all_objects, collection)

        location = sum((o.location for o in top_objects), Vector()) / len(top_objects)
        create_root_empty_for_collection(
            collection, location,
            objects_to_parent=top_objects,
            display_type=prefs.root_empty_display_type,
            display_size=prefs.root_empty_display_size,
            suffix=self.root_empty_suffix,
        )

        if self.mark_as_asset:
            collection.asset_mark()

        self.report({'INFO'}, f"Instance collection '{collection.name}' created.")

    def _create_for_hierarchy(self, context, top_obj, prefs):
        collection = bpy.data.collections.new(top_obj.name)
        parent = determine_parent_collection(context, top_object=top_obj)
        parent.children.link(collection)
        set_active_layer_Collection(collection.name)

        hierarchy = get_all_children_and_descendants(top_obj, include_top=True)
        _move_objects_to_collection(hierarchy, collection)

        create_root_empty_for_collection(
            collection, top_obj.location.copy(),
            objects_to_parent=[top_obj],
            display_type=prefs.root_empty_display_type,
            display_size=prefs.root_empty_display_size,
            suffix=self.root_empty_suffix,
        )

        if self.mark_as_asset:
            collection.asset_mark()


classes = (OBJECT_OT_CreateInstanceCollection,)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
