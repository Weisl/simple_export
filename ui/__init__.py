from . import export_panels, result_popups, ui_helpers, uilist, outliner, view3d_object_context_menu, \
    popup_list, engine_verify_panels

files = [
    export_panels,
    result_popups,
    ui_helpers,
    uilist,
    outliner,
    view3d_object_context_menu,
    popup_list,
    engine_verify_panels,
]


def register():
    for file in files:
        file.register()


def unregister():
    for file in reversed(files):
        file.unregister()
