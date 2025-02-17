import bpy
from mathutils import Matrix


def apply_location_offset(obj, collection_offset, inverse=False):
    """
    Adjusts the location of an object based on the collection's offset.
    """
    offset_matrix = Matrix.Translation(-collection_offset if not inverse else collection_offset)

    # Decompose the matrix_world into translation, rotation, and scale
    loc, rot, scale = obj.matrix_world.decompose()

    # Apply the offset to the location
    new_loc = offset_matrix @ Matrix.Translation(loc)

    # Rebuild the matrix_world with the modified location, maintaining rotation and scale
    obj.matrix_world = new_loc @ rot.to_matrix().to_4x4() @ Matrix.Diagonal(scale).to_4x4()


def apply_collection_offset(collection, inverse=False):
    """
    Applies or removes the collection's instance offset to all top-level objects in the collection.
    """
    collection_offset = collection.instance_offset

    for obj in collection.all_objects:
        if obj.parent is None:  # Only apply to top-level objects
            apply_location_offset(obj, collection_offset, inverse)



def update_collection_offset(scene):
    """Update the collection offset when the object is moved."""
    for collection in bpy.data.collections:
        obj = collection.get("root_object", None)
        if obj:
            obj_location = obj.location.copy()
            if collection.instance_offset != obj_location:
                # Set the collection offset to the object's location
                set_collection_offset(collection, obj_location)



def temporarily_disable_offset_handler():
    """Temporarily removes the collection offset update handler."""
    if update_collection_offset in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(update_collection_offset)


def reenable_offset_handler():
    """Re-enables the collection offset update handler."""
    if update_collection_offset not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(update_collection_offset)


def set_collection_offset(collection, location):
    """Set the offset of the specified collection to the given location."""
    if collection and collection.instance_offset:
        collection.instance_offset = location
    else:
        print(f"Collection '{collection.name}' does not have an instance offset.")