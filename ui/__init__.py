from . import export_panels, result_popups, ui_helpers, uilist, outliner, view3d_object_context_menu, popup_list, asset_browser_panel

files = [
    export_panels,
    result_popups,
    ui_helpers,
    uilist,
    outliner,
    view3d_object_context_menu,
    popup_list,
    asset_browser_panel,
]


def register():
    for file in files:
        file.register()


def unregister():
    for file in reversed(files):
        file.unregister()
