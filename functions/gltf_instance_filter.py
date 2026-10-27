import contextlib


def _gltf_tree_class():
    """Return the glTF exporter's VExportTree class, or None if this Blender build has no known location."""
    try:
        from io_scene_gltf2.blender.exp.tree import VExportTree  # Blender 4.2+
        return VExportTree
    except ImportError:
        pass
    try:
        from io_scene_gltf2.blender.exp.gltf2_blender_gather_tree import VExportTree  # older layouts
        return VExportTree
    except ImportError:
        return None


@contextlib.contextmanager
def skip_render_hidden_objects():
    """Leave objects that are disabled for render out of glTF exports, including inside collection instances.

    Blender's glTF option Renderable Objects (``use_renderable``) checks only objects the scene holds directly.
    Objects that come in through a collection instance inherit the instancer's result, so a collider or boolean
    cutter hidden for render inside an instanced collection is still exported as a visible mesh. While this context
    is active, the glTF exporter drops every hidden-for-render object. Other exporters are not affected.
    """
    tree_class = _gltf_tree_class()
    if tree_class is None or not hasattr(tree_class, "node_filter_not_inheritable_is_kept"):
        yield
        return

    original = tree_class.node_filter_not_inheritable_is_kept

    def node_filter_not_inheritable_is_kept(self, uuid):
        blender_object = self.nodes[uuid].blender_object
        if blender_object is not None and getattr(blender_object, "hide_render", False):
            return False
        return original(self, uuid)

    tree_class.node_filter_not_inheritable_is_kept = node_filter_not_inheritable_is_kept
    try:
        yield
    finally:
        tree_class.node_filter_not_inheritable_is_kept = original
