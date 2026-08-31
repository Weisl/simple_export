import bpy


def find_layer_collection_path(layer_coll, coll_name, _path=None):
    """Return the list of LayerCollections from the view-layer root down to
    (and including) the one wrapping *coll_name*, or None if not found."""
    _path = (_path or []) + [layer_coll]
    if layer_coll.name == coll_name:
        return _path
    for child in layer_coll.children:
        found = find_layer_collection_path(child, coll_name, _path)
        if found:
            return found
    return None


def ensure_layer_collection_included(collection_name):
    """Temporarily clear ``exclude`` on the target collection's LayerCollection
    and on any excluded ancestor, so Blender's collection exporters can see its
    objects.

    A collection that is excluded from the view layer (its Outliner checkbox is
    unticked) contributes no objects to the view layer, and Blender's collection
    exporters silently write an empty / no file for it. Re-including it for the
    duration of the export - then restoring - lets the geometry export with a
    warning instead of failing.

    Ancestors are cleared first (top-down) because a child stays out of the view
    layer while any ancestor is still excluded. Returns
    ``(was_excluded: bool, restore: callable)``; ``restore`` re-applies the
    original exclude state.
    """
    try:
        view_layer = bpy.context.view_layer
    except AttributeError:
        return False, lambda: None

    path = find_layer_collection_path(view_layer.layer_collection, collection_name)
    if not path:
        return False, lambda: None

    # path[0] is the master (scene root) LayerCollection - its exclude flag is
    # not user-meaningful and must not be toggled.
    to_restore = [lc for lc in path[1:] if lc.exclude]
    for lc in to_restore:
        lc.exclude = False

    def restore():
        for lc in reversed(to_restore):
            lc.exclude = True

    return bool(to_restore), restore


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
