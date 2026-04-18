import os

import bpy
from bpy.app.handlers import persistent

from .. import __package__ as base_package
from .export_path_func import generate_base_name


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


@persistent
def auto_update_export_paths_on_rename(depsgraph):
    """When a collection is renamed, update its exporter filepath to match the new name."""
    try:
        prefs = bpy.context.preferences.addons[base_package].preferences
        if not prefs.auto_update_path_on_rename:
            return
    except Exception:
        return

    scene = getattr(bpy.context, 'scene', None)
    if not scene:
        return

    prefix = getattr(scene, 'filename_prefix', '')
    suffix = getattr(scene, 'filename_suffix', '')
    blend_prefix = getattr(scene, 'filename_blend_prefix', False)
    separator = getattr(scene, 'filename_separator', '_')

    for collection in bpy.data.collections:
        old_name = collection.get("prev_name", collection.name)
        if old_name == collection.name:
            continue

        collection["prev_name"] = collection.name

        expected_old_base = generate_base_name(old_name, prefix, suffix, blend_prefix, separator)
        new_base = generate_base_name(collection.name, prefix, suffix, blend_prefix, separator)

        for exporter in collection.exporters:
            current_path = exporter.export_properties.filepath
            if not current_path:
                continue
            current_base = os.path.splitext(os.path.basename(current_path))[0]
            if current_base != expected_old_base:
                continue
            ext = os.path.splitext(current_path)[1]
            export_dir = os.path.dirname(current_path)
            exporter.export_properties.filepath = os.path.join(export_dir, f"{new_base}{ext}")


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
    bpy.app.handlers.depsgraph_update_post.append(auto_update_export_paths_on_rename)

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

    if auto_update_export_paths_on_rename in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(auto_update_export_paths_on_rename)


if __name__ == "__main__":
    register()
