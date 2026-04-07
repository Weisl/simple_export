import bpy
from bpy.app.handlers import persistent


@persistent
def update_collection_offset(depsgraph):
    """Update collection offsets for collections with an assigned root_object."""
    # DEBUG print("Depsgraph update triggered")

    for collection in bpy.data.collections:
        # Get the assigned offset object
        if collection.use_root_object:
            offset_obj = getattr(collection, "root_object", None)

            if offset_obj and isinstance(offset_obj, bpy.types.Object):
                # Check if instance_offset needs updating
                if collection.instance_offset != offset_obj.location:
                    # DEBUG print(f"Updating collection '{collection.name}' offset to: {offset_obj.location}")
                    collection.instance_offset = offset_obj.location


def ensure_collection_properties():
    """Ensure all collections have the addon properties set to their defaults.

    Needed for .blend files created before the addon was installed, or after
    a reload, where existing Collection instances may not yet carry the
    properties registered on bpy.types.Collection.
    """
    if not hasattr(bpy.types.Collection, "use_root_object"):
        return  # properties not registered yet — skip silently
    for collection in bpy.data.collections:
        if not hasattr(collection, "use_root_object"):
            collection.use_root_object = True
        if not hasattr(collection, "root_object"):
            collection.root_object = None
        if not hasattr(collection, "simple_export_selected"):
            collection.simple_export_selected = False


def load_post_handler(dummy):
    """Runs after a .blend file is loaded to ensure all collections have properties."""
    ensure_collection_properties()


def register():
    bpy.types.Collection.use_root_object = bpy.props.BoolProperty(
        name="Use Root Object",
        default=True,
        description="Specify Collection offset with a root object",
    )
    bpy.types.Collection.root_object = bpy.props.PointerProperty(
        name="Root Object",
        type=bpy.types.Object,
        description="Object to be used for setting the collection offset"
    )

    bpy.types.Collection.simple_export_selected = bpy.props.BoolProperty(
        name="Selected Collection",
        description="Select this collection for export",
        default=False)

    bpy.types.Collection.last_preset_name = bpy.props.StringProperty(
        name="Last Export Preset",
        description="Name of the last format export preset applied to this collection",
        default=""
    )

    bpy.types.Collection.last_addon_preset_name = bpy.props.StringProperty(
        name="Last Addon Preset",
        description="Name of the Simple Export addon preset active when this collection was configured",
        default=""
    )

    # Delay execution to ensure Blender has initialized bpy.data.collections
    bpy.app.timers.register(ensure_collection_properties, first_interval=0.1)

    # Register handler to ensure properties are set when loading an older .blend file
    bpy.app.handlers.load_post.append(load_post_handler)

    """add the handler."""
    if update_collection_offset not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(update_collection_offset)
        # print("Registered object location tracker")


def unregister():
    del bpy.types.Collection.root_object
    del bpy.types.Collection.use_root_object
    del bpy.types.Collection.simple_export_selected
    del bpy.types.Collection.last_preset_name
    del bpy.types.Collection.last_addon_preset_name

    """remove the handler."""
    if update_collection_offset in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_collection_offset)
        # print("Unregistered object location tracker")

    # Remove the load handler
    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)
