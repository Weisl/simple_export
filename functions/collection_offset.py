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


def apply_collection_offset(collection, offset, inverse=False):
    """
    Applies or removes the collection's instance offset to all top-level objects in the collection.
    """

    for obj in collection.objects:  # Use collection.objects to include hidden objects
        print(f"OBJECT: {obj.name}")
        if obj.parent is None:  # Only apply to top-level objects
            apply_location_offset(obj, offset, inverse)

def set_collection_offset(collection, location):
    """Set the offset of the specified collection to the given location."""
    if collection and collection.instance_offset:
        collection.instance_offset = location
    else:
        print(f"Collection '{collection.name}' does not have an instance offset.")
