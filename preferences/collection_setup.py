import bpy
from bpy.props import BoolProperty, FloatVectorProperty, PointerProperty
from bpy.app.handlers import persistent


class CollectionPreExportOps(bpy.types.PropertyGroup):
    """Per-collection pre-export operation settings."""
    move_by_collection_offset: BoolProperty(
        name="Move to Origin",
        description="Move objects to origin based on collection center/root object before export",
        default=False,
    )
    triangulate_before_export: BoolProperty(
        name="Triangulate Meshes",
        description="Add a Triangulate modifier to all meshes before export",
        default=False,
    )
    apply_scale_before_export: BoolProperty(
        name="Apply Scale",
        description="Bake object scale into mesh data before export",
        default=False,
    )
    apply_rotation_before_export: BoolProperty(
        name="Apply Rotation",
        description="Bake object rotation into mesh data before export",
        default=False,
    )
    apply_transform_before_export: BoolProperty(
        name="Apply Transformation",
        description="Bake location, rotation, and scale into mesh data before export",
        default=False,
    )
    pre_rotate_objects: BoolProperty(
        name="Pre-Rotate Objects",
        description="Apply a rotation offset to all objects before export",
        default=False,
    )
    pre_rotate_euler: FloatVectorProperty(
        name="Rotation Offset",
        description="Rotation offset (Euler XYZ) applied before export",
        subtype='EULER',
        default=(0.0, 0.0, 0.0),
    )


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


_PRE_EXPORT_BOOL_DEFAULTS = {
    'move_by_collection_offset': False,
    'triangulate_before_export': False,
    'apply_scale_before_export': False,
    'apply_rotation_before_export': False,
    'apply_transform_before_export': False,
    'pre_rotate_objects': False,
}

_PRE_EXPORT_BOOL_PROPS = list(_PRE_EXPORT_BOOL_DEFAULTS.keys())

_PRE_ROTATE_EULER_DEFAULT = (0.0, 0.0, 0.0)


def ensure_collection_properties():
    """Ensure all collections have the addon properties set to their defaults.

    Needed for .blend files created before the addon was installed, or after
    a reload, where existing Collection instances may not yet carry the
    properties registered on bpy.types.Collection.

    Also migrates legacy scene-level pre-export op values into each collection's
    pre_export_ops block on first load.
    """
    if not hasattr(bpy.types.Collection, "use_root_object"):
        return  # properties not registered yet — skip silently

    scene = bpy.context.scene if bpy.context else None

    for collection in bpy.data.collections:
        # Migrate legacy scene-level pre-export ops into per-collection settings.
        # Only runs if no per-collection values have been explicitly set yet,
        # detected by comparing each value against its registered default.
        # Note: checking truthiness alone would always detect 'triangulate_keep_normals'
        # as "custom" since its default is True, so we compare against known defaults.
        if scene and hasattr(collection, "pre_export_ops"):
            ops = collection.pre_export_ops
            has_custom = any(
                getattr(ops, attr) != default
                for attr, default in _PRE_EXPORT_BOOL_DEFAULTS.items()
            ) or tuple(ops.pre_rotate_euler) != _PRE_ROTATE_EULER_DEFAULT
            if not has_custom:
                for attr in _PRE_EXPORT_BOOL_PROPS:
                    if hasattr(scene, attr):
                        setattr(ops, attr, getattr(scene, attr))
                if hasattr(scene, 'pre_rotate_euler'):
                    ops.pre_rotate_euler = scene.pre_rotate_euler


def load_post_handler(dummy):
    """Runs after a .blend file is loaded to ensure all collections have properties."""
    ensure_collection_properties()


def _get_filepath_proxy(self):
    try:
        scene = bpy.context.scene
        format_filter = scene.filter_format if scene.filter_format != 'ALL' else None
        from ..functions.exporter_funcs import find_exporter
        exporter = find_exporter(self, format_filter=format_filter)
        if exporter:
            return exporter.export_properties.filepath
    except Exception:
        pass
    return ""


def _set_filepath_proxy(self, value):
    try:
        scene = bpy.context.scene
        format_filter = scene.filter_format if scene.filter_format != 'ALL' else None
        from ..functions.exporter_funcs import find_exporter
        exporter = find_exporter(self, format_filter=format_filter)
        if exporter:
            exporter.export_properties.filepath = value
    except Exception:
        pass


def register():
    bpy.utils.register_class(CollectionPreExportOps)
    bpy.types.Collection.pre_export_ops = PointerProperty(type=CollectionPreExportOps)

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

    bpy.types.Collection.simple_export_export_preset = bpy.props.StringProperty(
        name="Last Export Format Preset",
        description="Name of the last format export format preset applied to this collection",
        default=""
    )

    bpy.types.Collection.simple_export_addon_preset = bpy.props.StringProperty(
        name="Last Addon Preset",
        description="Name of the Simple Export addon preset active when this collection was configured",
        default=""
    )

    bpy.types.Collection.last_export_failed = bpy.props.BoolProperty(
        name="Last Export Failed",
        description="The most recent export attempt for this collection failed",
        default=False,
    )

    bpy.types.Collection.export_group_name = bpy.props.StringProperty(
        name="Export Group",
        description="Custom group name for filtering this collection in the export list",
        default="",
    )

    # Proxy property without FILE_PATH subtype to avoid Blender's red "file not found"
    # validation on export destinations (both relative // and absolute paths are valid).
    bpy.types.Collection.simple_export_filepath_proxy = bpy.props.StringProperty(
        name="Export Path",
        description="Export file path for this collection",
        get=_get_filepath_proxy,
        set=_set_filepath_proxy,
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
    del bpy.types.Collection.pre_export_ops
    bpy.utils.unregister_class(CollectionPreExportOps)

    del bpy.types.Collection.root_object
    del bpy.types.Collection.use_root_object
    del bpy.types.Collection.simple_export_selected
    del bpy.types.Collection.simple_export_export_preset
    del bpy.types.Collection.simple_export_addon_preset
    del bpy.types.Collection.last_export_failed
    del bpy.types.Collection.export_group_name
    del bpy.types.Collection.simple_export_filepath_proxy

    """remove the handler."""
    if update_collection_offset in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_collection_offset)
        # print("Unregistered object location tracker")

    # Remove the load handler
    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)
