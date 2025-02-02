# support reloading sub-modules
if "bpy" in locals():
    import importlib

    importlib.reload(operators)
    importlib.reload(preferences)
    importlib.reload(ui)

else:
    from . import operators
    from . import preferences
    from . import ui


def register():
    # call the register function of the submodules.
    operators.register()
    ui.register()
    preferences.register()


def unregister():
    # call unregister function of the submodules.
    ui.unregister()
    preferences.unregister()
    operators.unregister()


if __name__ == "__main__":
    register()
