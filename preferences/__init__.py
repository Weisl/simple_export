from . import keymap, preferenecs, collection_setup, engine_connections

files = [
    engine_connections,  # before preferenecs: SIMPLE_EXPORT_preferences'
                          # class body references EngineConnectionSettings in
                          # a PointerProperty, so that type must already be
                          # register_class()'d by the time preferenecs
                          # registers SIMPLE_EXPORT_preferences.
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
