import os

import bpy

from .collection_layer import set_active_layer_Collection
from .preset_func import assign_preset
from .. import __package__ as base_package
from ..core.export_formats import ExportFormats
from ..core.export_path_func import assign_export_path_to_exporter


def generate_collection_name(context, obj_name):
    prefs = context.preferences.addons[base_package].preferences
    scene = context.scene
    settings_col = scene if scene.overwrite_collection_settings else prefs

    collection_name = obj_name
    if getattr(settings_col, 'use_blend_file_name_as_prefix'):
        blend_file_name = os.path.splitext(os.path.basename(bpy.data.filepath))[0]
        if not collection_name.startswith(blend_file_name):
            collection_name = blend_file_name + "_" + collection_name

    prefix = getattr(settings_col, 'custom_prefix')
    suffix = getattr(settings_col, 'custom_suffix')

    if prefix and not collection_name.startswith(prefix):
        collection_name = prefix + "_" + collection_name

    if suffix and not collection_name.endswith(suffix):
        collection_name = collection_name + "_" + suffix

    return collection_name


def setup_collection(context, collection, active_object, settings_col, settings_filepath):
    scene = context.scene
    prefs = context.preferences.addons[base_package].preferences

    # Set collection properties
    collection['simple_export_selected'] = True
    color_tag = getattr(settings_col, 'collection_color')
    collection.color_tag = color_tag

    if getattr(settings_col, 'set_location_offset_on_creation'):
        collection.instance_offset = active_object.location

    # Assign exporter
    set_active_layer_Collection(collection.name)

    export_data = ExportFormats.get(scene.export_format)

    if not export_data:
        raise ValueError(f"Invalid export format: {scene.export_format}")

    def get_all_exporters():
        return list(collection.exporters)

    exporters_before = get_all_exporters()

    export_data = ExportFormats.get(scene.export_format)
    operator_name = export_data.op_name

    bpy.ops.collection.exporter_add(name=operator_name)
    exporters_after = get_all_exporters()

    exporter = list(set(exporters_after) - set(exporters_before))[0]

    if getattr(settings_col, 'auto_set_preset'):
        # Construct the property name dynamically
        export_format = scene.export_format.lower()
        prop_name = f"simple_export_preset_file_{export_format}"

        # Get preset path
        preset_settings = scene if scene.overwrite_preset_settings else prefs
        preset_path = getattr(preset_settings, prop_name, None)

        assign_preset(exporter, preset_path)

    if getattr(settings_col, 'auto_set_filepath'):
        success, export_path, msg = assign_export_path_to_exporter(collection, exporter, scene, settings_filepath)

    return exporter
