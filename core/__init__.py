from . import export_manager

files = [
    export_manager,
]


def register():
    for file in files:
        file.register()


def unregister():
    for file in reversed(files):
        file.unregister()
