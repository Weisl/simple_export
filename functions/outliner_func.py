import bpy


def get_outliner_collections(context):
    # Get all selected items in the outliner
    selected_ids = context.selected_ids

    return [item for item in selected_ids if isinstance(item, bpy.types.Collection)]
