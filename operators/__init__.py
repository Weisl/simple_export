from . import assign_exporter, export_ops, filepath_ops, preset_ops, ui_ops, create_exporter

files = [
    assign_exporter,
    export_ops,
    filepath_ops,
    preset_ops,
    ui_ops,
    create_exporter,
]


def register():
    for file in files:
        file.register()


def unregister():
    for file in reversed(files):
        file.unregister()
