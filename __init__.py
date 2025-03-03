# support reloading sub-modules
if "bpy" in locals():
    import importlib

    importlib.reload(operators)
    importlib.reload(preferences)
    importlib.reload(ui)
    importlib.reload(core)
    importlib.reload(presets)

else:
    from . import operators
    from . import preferences
    from . import ui
    from . import core
    from . import presets


def register():
    # call the register function of the submodules.
    operators.register()
    ui.register()
    preferences.register()
    core.register()
    presets.register()


def unregister():
    # call unregister function of the submodules.
    presets.unregister()
    core.unregister()
    ui.unregister()
    preferences.unregister()
    operators.unregister()


if __name__ == "__main__":
    register()
