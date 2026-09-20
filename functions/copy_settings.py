import os
import warnings

from .collection_layer import ensure_layer_collection_included
from .exporter_funcs import add_extension, create_collection_exporter, find_exporter, remove_all_collection_exporters
from ..core.export_formats import ExportFormats

# Exporter properties that belong to one specific collection and must not follow the settings
# to another: 'filepath' is unique per collection, 'use_selection' mirrors the ignore list of
# assign_preset(), and 'collection' is the export-source filter of the operator.
EXPORTER_COPY_SKIP = frozenset({'filepath', 'collection', 'use_selection'})


def copy_rna_properties(source, target, skip=()):
    """Copy every writable RNA property from source to target.

    Works for anything exposing bl_rna (exporter operator properties, PropertyGroups), so
    properties added in a later Blender version or add-on release are picked up without
    maintaining a list of names.

    Returns:
        list: identifiers of the properties that could not be copied.
    """
    failed = []
    for prop in source.bl_rna.properties:
        name = prop.identifier
        if name == 'rna_type' or prop.is_readonly or name in skip:
            continue
        try:
            setattr(target, name, getattr(source, name))
        except Exception as e:
            print(f"Could not copy property '{name}': {e}")
            failed.append(name)
    return failed


def _restore_filepath(exporter, old_path):
    """Give a converted exporter its previous folder and file name, with the new format's extension."""
    if not old_path:
        return

    is_directory = old_path.endswith(('/', '\\'))
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*does not support blend relative.*", category=RuntimeWarning)
        if is_directory:
            exporter.export_properties.filepath = old_path
        else:
            exporter.export_properties.filepath = os.path.splitext(old_path)[0]
            exporter.export_properties.filepath = add_extension(exporter)


def _copy_exporter_settings(operator, context, source, target):
    """Copy the exporter properties, converting the target's exporter to the source's format if needed.

    Returns:
        tuple: (message, failed_properties). message is None when the copy was not possible.
    """
    source_exporter = find_exporter(source)
    if not source_exporter:
        return None, []

    format_key = ExportFormats.get_key_from_op_type(str(type(source_exporter.export_properties)))
    if not format_key:
        return None, []

    converted = False
    target_exporter = find_exporter(target, format_filter=format_key)
    if not target_exporter:
        # Different format or no exporter yet: replace it, keeping the folder and file name
        previous_exporter = find_exporter(target)
        previous_path = previous_exporter.export_properties.filepath if previous_exporter else ''

        # A collection excluded from the view layer cannot be made active for exporter_add
        _was_excluded, restore_exclude = ensure_layer_collection_included(target.name)
        try:
            remove_all_collection_exporters(target)
            target_exporter = create_collection_exporter(operator, context, target, export_format=format_key)
        finally:
            restore_exclude()

        if not target_exporter:
            return None, []
        converted = True

    failed = copy_rna_properties(source_exporter.export_properties, target_exporter.export_properties,
                                 skip=EXPORTER_COPY_SKIP)

    if converted:
        _restore_filepath(target_exporter, previous_path)

    # Keep the "last applied preset" labels so the modified marker in the list stays correct
    target.simple_export_export_preset = source.simple_export_export_preset
    target.simple_export_addon_preset = source.simple_export_addon_preset

    message = f"exporter settings ({format_key})"
    if converted:
        message += " (converted exporter)"
    return message, failed


def copy_collection_export_settings(operator, context, source, target, exporter=True, pre_export=True,
                                    group=True):
    """Copy the export settings of source to target. File paths are never copied.

    Returns:
        dict: {'name', 'success', 'message'}, the same shape the preset operators report.
    """
    copied = []
    failed = []

    if exporter:
        message, failed_props = _copy_exporter_settings(operator, context, source, target)
        if message is None:
            return {'name': target.name, 'success': False, 'message': "Failed to copy exporter settings."}
        copied.append(message)
        failed.extend(failed_props)

    if pre_export and hasattr(source, 'pre_export_ops') and hasattr(target, 'pre_export_ops'):
        failed.extend(copy_rna_properties(source.pre_export_ops, target.pre_export_ops))
        copied.append("pre-export operations")

    if group:
        target.export_group_name = source.export_group_name
        copied.append("user group")

    message = "Copied " + ", ".join(copied) + "."
    if failed:
        message += f" Could not copy: {', '.join(failed)}."
    return {'name': target.name, 'success': True, 'message': message}
