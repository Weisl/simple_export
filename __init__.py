# support reloading sub-modules
if "bpy" in locals():
    import importlib

    importlib.reload(operators)
    importlib.reload(preferences)
    importlib.reload(presets)
    importlib.reload(ui)

else:
    from . import operators
    from . import preferences
    from . import presets
    from . import ui


def register():
    # call the register function of the submodules.
    operators.register()
    presets.register()
    preferences.register()
    ui.register()


def unregister():
    # call unregister function of the submodules.
    ui.unregister()
    preferences.unregister()
    presets.unregister()
    operators.unregister()


if __name__ == "__main__":
    register()
