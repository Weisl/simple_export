_PRE_EXPORT_BOOL_PROPS = [
    'move_by_collection_offset',
    'triangulate_before_export',
    'triangulate_keep_normals',
    'apply_scale_before_export',
    'apply_rotation_before_export',
    'apply_transform_before_export',
    'pre_rotate_objects',
]


def setup_collection_properties(prop, collection, base_object=None):
    collection.simple_export_selected = True
    if prop.collection_color != 'NONE':
        collection.color_tag = prop.collection_color
    if prop.collection_instance_offset and hasattr(collection, 'instance_offset'):
        collection.instance_offset = base_object.location if base_object else (0, 0, 0)
    if getattr(prop, 'create_empty_root', False) and hasattr(collection, 'use_root_object'):
        if not (collection.use_root_object and collection.root_object):
            from ..operators.collection_offset_ops import create_root_empty_for_collection
            from mathutils import Vector
            import bpy as _bpy
            from .. import __package__ as base_package
            _prefs = _bpy.context.preferences.addons[base_package].preferences
            location = base_object.location.copy() if base_object else Vector((0.0, 0.0, 0.0))
            collection_objects_set = set(collection.objects)
            top_level_objects = [
                obj for obj in collection.objects
                if obj.parent is None or obj.parent not in collection_objects_set
            ]
            # If there is exactly one top-level object and it is an empty, treat it
            # as the intentional root rather than creating a duplicate.
            if len(top_level_objects) == 1 and top_level_objects[0].type == 'EMPTY':
                collection.use_root_object = True
                collection.root_object = top_level_objects[0]
            else:
                create_root_empty_for_collection(
                    collection, location, top_level_objects,
                    display_type=_prefs.root_empty_display_type,
                    display_size=_prefs.root_empty_display_size,
                    suffix=getattr(prop, 'root_empty_suffix', '_root'),
                )
    elif prop.use_root_object and hasattr(collection, 'use_root_object'):
        collection.use_root_object = prop.use_root_object
        if base_object:
            collection.root_object = base_object

    # Seed per-collection pre-export ops from operator props (set by preset) or scene fallback
    if hasattr(collection, 'pre_export_ops'):
        import bpy
        scene = bpy.context.scene
        ops = collection.pre_export_ops
        for attr in _PRE_EXPORT_BOOL_PROPS:
            if hasattr(prop, attr):
                setattr(ops, attr, getattr(prop, attr))
            elif hasattr(scene, attr):
                setattr(ops, attr, getattr(scene, attr))
        if hasattr(prop, 'pre_rotate_euler'):
            ops.pre_rotate_euler = prop.pre_rotate_euler
        elif hasattr(scene, 'pre_rotate_euler'):
            ops.pre_rotate_euler = scene.pre_rotate_euler

    return collection


def create_collection(collection_name):
    """Create a collection if it doesn't exist and link it to the current scene if not already linked."""
    import bpy

    # Create the collection if it doesn't exist
    if collection_name not in bpy.data.collections:
        collection = bpy.data.collections.new(collection_name)
    else:
        collection = bpy.data.collections[collection_name]

    # Get the current scene
    current_scene = bpy.context.scene

    # Link to current scene if not already linked
    if collection.name not in current_scene.collection.children:
        current_scene.collection.children.link(collection)

    # collection.color_tag = color_tag

    return collection
