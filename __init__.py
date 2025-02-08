# support reloading sub-modules
if "bpy" in locals():
    import importlib

    importlib.reload(operators)
    importlib.reload(preferences)
    importlib.reload(ui)
    importlib.reload(core)

else:
    from . import operators
    from . import preferences
    from . import ui
    from . import core


def register():
    # call the register function of the submodules.
    operators.register()
    ui.register()
    preferences.register()
    core.register()


def unregister():
    # call unregister function of the submodules.
    core.unregister()
    ui.unregister()
    preferences.unregister()
    operators.unregister()


if __name__ == "__main__":
    register()
