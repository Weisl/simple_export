from . import keymap, preferenecs, collection_setup

files = [
    preferenecs,
    keymap,
    collection_setup
]


def register():
    for file in files:
        file.register()


def unregister():
    for file in reversed(files):
        file.unregister()
