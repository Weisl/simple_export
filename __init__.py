# support reloading sub-modules
# if "bpy" in locals():
#     import importlib
#
#     importlib.reload(uilist)
#     importlib.reload(collection_utils)
#     importlib.reload(operators)
#     importlib.reload(panels)
#     importlib.reload(keymap)
#     importlib.reload(preferences)
#
# else:
from . import preferenecs
from . import collection_utils
from . import operators
from . import uilist
from . import panels
from . import keymap


files = [
    collection_utils,
    operators,
    uilist,
    panels,

    # keymap and preferences should be last
    keymap,
    preferenecs, ]


def register():
    for file in files:
        file.register()


def unregister():
    for file in files.reverse():
        file.unregister()


if __name__ == "__main__":
    register()
