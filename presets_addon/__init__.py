from . import exporter_preset

files = [
    exporter_preset
]

def initialize_presets():
    pass
    # TODO: Initialize the presets for the addon

def register():
    for file in files:
        file.register()

def unregister():
    for file in reversed(files):
        file.unregister()


