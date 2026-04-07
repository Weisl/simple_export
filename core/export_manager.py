import bpy


def ensure_previous_name_stored():
    """ Ensures each collection has a stored previous name for tracking. """
    for collection in bpy.data.collections:
        if "prev_name" not in collection.keys():  # Only set if missing
            collection["prev_name"] = collection.name


def check_collection_name_changes():
    """ Checks for name changes and prints updates before modifying values. """
    renamed_collections = []
    collection_states = {}  # Stores the original previous names

    for collection in bpy.data.collections:
        prev_name = collection.get("prev_name", collection.name)  # Safely get previous name
        collection_states[collection.name] = prev_name  # Save the state before updating

        if prev_name != collection.name:  # Collection was renamed
            renamed_collections.append((prev_name, collection.name))

    # Print rename messages *before* updating
    # for old_name, new_name in renamed_collections:
    #     print(f"[Collection Tracker] Collection renamed: '{old_name}' → '{new_name}'")

    # Now update prev_name for future checks
    for collection in bpy.data.collections:
        collection["prev_name"] = collection.name

    return collection_states  # Return previous state for correct output


def check_on_file_load(dummy):
    """ Runs after a file is loaded to reinitialize previous names. """
    ensure_previous_name_stored()


class PRINT_OT_collection_names(bpy.types.Operator):
    """Prints all collection names in the console"""
    bl_idname = "collection.print_names"
    bl_label = "Print Collection Names"

    def execute(self, context):
        # DEBUG: print("[Collection Tracker] Checking for changes before execution...")

        ensure_previous_name_stored()  # Ensure all collections have `prev_name`
        previous_states = check_collection_name_changes()  # Detect renames & get previous names

        #DEBUG print("[Collection Tracker] Current Collections:")
        for collection in bpy.data.collections:
            prev_name = previous_states.get(collection.name, collection.name)  # Use stored state
            #DEBUG: print(f" - {collection.name} (Previous: {prev_name})")

        return {'FINISHED'}


classes = (PRINT_OT_collection_names,)


# Register add-on
def register():
    bpy.app.handlers.load_post.append(check_on_file_load)  # Ensure names persist when opening files

    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.app.timers.register(ensure_previous_name_stored, first_interval=0.1)  # Delay execution


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)

    if check_on_file_load in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(check_on_file_load)  # Remove handler on unregister


if __name__ == "__main__":
    register()
