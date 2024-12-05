import bpy

class EXPORT_OT_CreateExportCollection(bpy.types.Operator):
    """
    Create a new collection for the active object and its children.
    """
    bl_idname = "simple_export.create_export_collection"
    bl_label = "Create Export Collection"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        active_object = context.active_object
        parent_collection = context.scene.parent_collection or context.scene.collection

        # Check for active object
        if not active_object:
            self.report({'WARNING'}, "No active object selected.")
            return {'CANCELLED'}

        # Ensure parent_collection is a valid bpy.types.Collection
        if not isinstance(parent_collection, bpy.types.Collection):
            self.report({'WARNING'}, "No valid parent collection selected. Falling back to the scene collection.")
            parent_collection = context.scene.collection

        # Helper function to create or retrieve an existing collection
        def make_collection(collection_name, parent_collection):
            """
            Return existing collection if it exists, otherwise create a new one
            """
            if collection_name in bpy.data.collections:
                col = bpy.data.collections[collection_name]
            else:
                col = bpy.data.collections.new(collection_name)
                if col.name not in parent_collection.children.keys():
                    parent_collection.children.link(col)
            return col

        # Create or get the export collection
        export_collection = make_collection(active_object.name, parent_collection)

        # Recursive function to find all children of an object
        def find_children(parent_object, child_stack):
            """ Recursive function to find all children """
            for ob in bpy.data.objects:
                if ob.parent == parent_object:
                    child_stack.append(ob)
                    find_children(ob, child_stack)
            return child_stack

        # Find all children of the active object
        collection_objects = find_children(active_object, [])
        collection_objects.append(active_object)  # Add the active object itself

        # Link objects to the new collection
        for ob in collection_objects:
            # Avoid redundant linking
            if export_collection not in ob.users_collection:
                export_collection.objects.link(ob)

            # Unlink the object from other collections
            for col in ob.users_collection:
                if col != export_collection:
                    col.objects.unlink(ob)

        # Set instance offset
        export_collection.instance_offset = active_object.location

        self.report({'INFO'}, f"Export collection '{export_collection.name}' created successfully.")
        return {'FINISHED'}

classes = (
    EXPORT_OT_CreateExportCollection,
)

# Register the scene property
def register():
    from bpy.utils import register_class
    Scene = bpy.types.Scene
    Scene.parent_collection = bpy.props.PointerProperty(
        name="Parent Collection",
        description="Choose the parent collection to link the new collection to",
        type=bpy.types.Collection
    )
    for cls in classes:
        register_class(cls)

def unregister():
    from bpy.utils import unregister_class
    Scene = bpy.types.Scene
    del Scene.parent_collection
    for cls in reversed(classes):
        unregister_class(cls)


