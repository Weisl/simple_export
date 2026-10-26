import bpy


def find_layer_collection_path(layer_coll, coll_name, _path=None):
    """Return the list of LayerCollections from the view-layer root down to
    (and including) the one wrapping *coll_name*, or None if not found."""
    _path = (_path or []) + [layer_coll]
    if layer_coll.name == coll_name:
        return _path
    for child in layer_coll.children:
        found = find_layer_collection_path(child, coll_name, _path)
        if found:
            return found
    return None


def ensure_layer_collection_included(collection_name):
    """Temporarily clear ``exclude`` on the target collection's LayerCollection
    and on any excluded ancestor, so Blender's collection exporters can see its
    objects.

    A collection that is excluded from the view layer (its Outliner checkbox is
    unticked) contributes no objects to the view layer, and Blender's collection
    exporters silently write an empty / no file for it. Re-including it for the
    duration of the export - then restoring - lets the geometry export with a
    warning instead of failing.

    Ancestors are cleared first (top-down) because a child stays out of the view
    layer while any ancestor is still excluded. Returns
    ``(was_excluded: bool, restore: callable)``; ``restore`` re-applies the
    original exclude state.
    """
    try:
        view_layer = bpy.context.view_layer
    except AttributeError:
        return False, lambda: None

    path = find_layer_collection_path(view_layer.layer_collection, collection_name)
    if not path:
        return False, lambda: None

    # path[0] is the master (scene root) LayerCollection - its exclude flag is
    # not user-meaningful and must not be toggled.
    to_restore = [lc for lc in path[1:] if lc.exclude]
    for lc in to_restore:
        lc.exclude = False

    def restore():
        for lc in reversed(to_restore):
            lc.exclude = True

    return bool(to_restore), restore


class ViewLayerIsolation:
    """Keep only one collection in the active view layer while it exports.

    Animation exporters (glTF, FBX, USD, Alembic) step the scene once per baked
    frame, and every step re-evaluates everything in the view layer. In a level
    file with many rigs, exporting one character then re-evaluates all of them
    on every frame (measured: 41 NPCs, 209 s together vs 35 s isolated).

    ``isolate()`` excludes every LayerCollection that is neither the target, its
    subtree nor one of its ancestors, and disables loose scene-root objects in
    viewports. It also re-includes an excluded target (the job
    ``ensure_layer_collection_included`` does without isolation). Objects the
    target depends on (armatures, modifier targets, drivers) are still
    evaluated, because the depsgraph pulls in dependencies regardless of
    view-layer exclusion.

    The original state is captured once on the first ``isolate()`` and restored
    once by ``restore()``, so a batch export re-evaluates the full scene only
    one time, at the end.
    """

    def __init__(self, view_layer, scene):
        self.view_layer = view_layer
        self.scene = scene
        self._exclude_backup = None  # [(path of collection names, exclude)], pre-order
        self._hidden_objects = []

    @property
    def active(self):
        return self._exclude_backup is not None

    def _walk(self, lc=None, path=()):
        """Yield (name path, LayerCollection) below *lc*, parents first.

        The backup stores name paths, not LayerCollections: toggling ``exclude``
        resyncs the view layer, so stored RNA pointers are not safe to reuse.
        """
        for child in (lc or self.view_layer.layer_collection).children:
            child_path = path + (child.name,)
            yield child_path, child
            yield from self._walk(child, child_path)

    def isolate(self, collection_name):
        """Isolate *collection_name*; return True if it (or an ancestor) was
        originally excluded from the view layer."""
        collection = bpy.data.collections.get(collection_name)
        if collection is None:
            return False
        if self._exclude_backup is None:
            self._exclude_backup = [(path, lc.exclude) for path, lc in self._walk()]
        original = dict(self._exclude_backup)
        self._restore_objects()
        was_excluded = False

        # Setting ``exclude`` also sets it on every child, so this walks top-down
        # and fixes the children after their parent.
        def walk(lc, path):
            nonlocal was_excluded
            for child in lc.children:
                child_path = path + (child.name,)
                is_target = child.collection == collection
                if is_target or collection in child.collection.children_recursive:
                    # target or ancestor: must be included to export the target
                    was_excluded |= original.get(child_path, False)
                    if child.exclude:
                        child.exclude = False
                    if not is_target:
                        walk(child, child_path)
                        continue
                    # the target's subtree goes back to its original state
                    for sub_path, sub in list(self._walk(child, child_path)):
                        exclude = original.get(sub_path, sub.exclude)
                        if sub.exclude != exclude:
                            sub.exclude = exclude
                elif not child.exclude:
                    child.exclude = True

        walk(self.view_layer.layer_collection, ())

        # Loose scene-root objects are not in any child collection, so the
        # exclusion above does not reach them.
        keep = set(collection.all_objects)
        for obj in self.scene.collection.objects:
            if obj in keep or obj.hide_viewport:
                continue
            try:
                obj.hide_viewport = True
            except (AttributeError, RuntimeError):  # linked, non-overridable object
                continue
            self._hidden_objects.append(obj)

        return was_excluded

    def _restore_objects(self):
        for obj in self._hidden_objects:
            try:
                obj.hide_viewport = False
            except ReferenceError:  # object removed during export
                pass
        self._hidden_objects = []

    def _find(self, path):
        lc = self.view_layer.layer_collection
        for name in path:
            lc = lc.children.get(name)
            if lc is None:
                return None
        return lc

    def restore(self):
        self._restore_objects()
        if self._exclude_backup is None:
            return
        # Parents first: setting ``exclude`` recurses into the children, which
        # then get their own original state back right after.
        for path, exclude in self._exclude_backup:
            lc = self._find(path)
            if lc is not None and lc.exclude != exclude:
                lc.exclude = exclude
        self._exclude_backup = None


def recursiveLayerCollection(layerColl, collName):
    # DEBUG: print(f"Checking collection: {layerColl.name}")  # Debug print
    if layerColl.name == collName:
        # DEBUG: print(f"Found collection: {collName}")  # Debug print
        return layerColl
    for layer in layerColl.children:
        found = recursiveLayerCollection(layer, collName)
        if found:
            return found
    return None


def set_active_layer_Collection(collection_name):
    # Switching active Collection to active Object selected
    layer_collection = bpy.context.view_layer.layer_collection
    layerColl = recursiveLayerCollection(layer_collection, collection_name)
    bpy.context.view_layer.active_layer_collection = layerColl
