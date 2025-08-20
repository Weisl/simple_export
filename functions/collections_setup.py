def setup_collection_properties(prop, collection, base_object=None):
    collection.simple_export_selected = True
    if prop.collection_color != 'NONE':
        collection.color_tag = prop.collection_color
    if prop.collection_instance_offset and hasattr(collection, 'instance_offset'):
        collection.instance_offset = base_object.location if base_object else (0, 0, 0)
    if prop.use_root_object and hasattr(collection, 'use_root_object'):
        collection.use_root_object = prop.use_root_object
    if prop.use_root_object and base_object:
        collection.root_object = base_object
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
