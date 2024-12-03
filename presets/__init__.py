from . import naming_preset
from . import presets_data
from . import preset_operator
from . import convert_old_presets

files = (
    naming_preset,
    preset_operator,
    convert_old_presets
)

def register():
    for file in files:
        file.register()

def unregister():
    for file in reversed(files):
        file.unregister()
