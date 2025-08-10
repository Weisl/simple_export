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
