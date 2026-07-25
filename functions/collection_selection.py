import bpy


def get_export_collection_list(context, outliner=False, individual_collection=False, collection_name=''):
    """Return the list of collections an export/validate operation should act on.

    Shared by SCENE_OT_ExportCollectionsSelection and the validation operators so
    both use the exact same outliner/individual/selected-list semantics.
    """
    if outliner:
        from .outliner_func import get_outliner_collections
        return get_outliner_collections(context)

    if individual_collection:
        collection = bpy.data.collections.get(collection_name)
        return [collection] if collection else []

    scene = context.scene
    from ..ui.uilist import collection_passes_uilist_filters
    return [
        col for col in bpy.data.collections
        if getattr(col, "simple_export_selected", False)
        and collection_passes_uilist_filters(col, scene)
    ]
