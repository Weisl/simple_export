# support reloading sub-modules
if "bpy" in locals():
    import importlib

    importlib.reload(operators)
    importlib.reload(ui)
    importlib.reload(preferences)
    importlib.reload(core)
    importlib.reload(presets_export)
    importlib.reload(presets_addon)
    importlib.reload(validation)

else:
    from . import operators
    from . import ui
    from . import preferences
    from . import core
    from . import presets_export
    from . import presets_addon
    from . import validation


def register():
    # call the register function of the submodules.
    operators.register()
    ui.register()
    preferences.register()
    core.register()
    presets_export.register()
    presets_addon.register()
    validation.register()


def unregister():
    # call unregister function of the submodules.
    validation.unregister()
    presets_addon.unregister()
    presets_export.unregister()
    core.unregister()
    preferences.unregister()
    ui.unregister()
    operators.unregister()


if __name__ == "__main__":
    register()
