from . import exporter_preset

files = [
    exporter_preset
]

def register():
    for file in files:
        file.register()

def unregister():
    for file in reversed(files):
        file.unregister()


