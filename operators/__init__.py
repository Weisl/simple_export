from . import assign_exporter, export_ops, filepath_ops, preset_ops, ui_ops, create_exporter, collection_offset_ops

files = [
    assign_exporter,
    export_ops,
    filepath_ops,
    preset_ops,
    ui_ops,
    create_exporter,
    collection_offset_ops,
]


def register():
    for file in files:
        file.register()


def unregister():
    for file in reversed(files):
        file.unregister()
