from . import n_panel, properties_panels, result_popups, ui_helpers, uilist, outliner

files = [
    n_panel,
    properties_panels,
    result_popups,
    ui_helpers,
    uilist,
    outliner,
]


def register():
    for file in files:
        file.register()


def unregister():
    for file in reversed(files):
        file.unregister()
