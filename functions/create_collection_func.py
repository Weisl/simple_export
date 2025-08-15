import bpy

from .collection_layer import set_active_layer_Collection
from .preset_func import assign_preset
from .. import __package__ as base_package
from ..core.export_formats import ExportFormats
from ..core.export_path_func import assign_export_path_to_exporter


def setup_collection(context, collection, active_object, settings_col, settings_filepath, settings_filename):
    scene = context.scene
    prefs = context.preferences.addons[base_package].preferences

    # Set collection properties
    collection.simple_export_selected = True
    color_tag = getattr(settings_col, 'collection_color')
    collection.color_tag = color_tag

    if getattr(settings_col, 'collection_instance_offset'):
        collection.instance_offset = active_object.location

    if getattr(settings_col, 'use_root_object'):
        collection.use_root_object = settings_col.use_root_object

    if getattr(settings_col, 'collection_set_root_offset_object'):
        collection.root_object = active_object

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

    if getattr(settings_col, 'assign_preset'):
        # Construct the property name dynamically
        export_format = scene.export_format.lower()
        prop_name = f"simple_export_preset_file_{export_format}"

        # Get preset path
        preset_settings = scene
        preset_path = getattr(preset_settings, prop_name, None)

        assign_preset(exporter, preset_path)

    if getattr(settings_col, 'set_export_path'):
        success, export_path, msg = assign_export_path_to_exporter(collection, exporter, scene, settings_filepath,
                                                                   settings_filename, use_defaults=True)

    return exporter
