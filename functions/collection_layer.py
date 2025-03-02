import bpy


def recursiveLayerCollection(layerColl, collName):
    # DEBUG: print(f"Checking collection: {layerColl.name}")  # Debug print
    if layerColl.name == collName:
        # DEBUG: print(f"Found collection: {collName}")  # Debug print
        return layerColl
    for layer in layerColl.children:
        found = recursiveLayerCollection(layer, collName)
        if found:
            return found
    return None


def set_active_layer_Collection(collection_name):
    # Switching active Collection to active Object selected
    layer_collection = bpy.context.view_layer.layer_collection
    layerColl = recursiveLayerCollection(layer_collection, collection_name)
    bpy.context.view_layer.active_layer_collection = layerColl
