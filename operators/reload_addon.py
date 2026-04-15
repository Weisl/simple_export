import bpy
from bpy.types import Operator


class VIEW3D_OT_simple_export_reload(Operator):
    """Reload all Simple Export scripts."""
    bl_idname      = "simple_export.reload_addon"
    bl_label       = "Reload Addon"
    bl_description = "Reload all Simple (Collection) Export scripts"

    def execute(self, context):
        import importlib
        import sys

        # Derive the addon root package name by stripping the sub-package suffix.
        # Works for both legacy addons ("simple_export.operators")
        # and extensions   ("bl_ext.user_default.simple_export.operators").
        root_pkg = __package__.rsplit(".", 1)[0]

        # Snapshot the module names now, before any reload happens.
        # Sort key: deeper modules first (so core.* sub-modules reload before
        # core.__init__), and alphabetically within the same depth so that
        # "core.*" always reloads before "operators.*" before "ui.*".
        mod_names = sorted(
            [name for name in sys.modules
             if name == root_pkg or name.startswith(root_pkg + ".")],
            key=lambda n: (-n.count("."), n),
        )

        # Defer the actual reload to the next event-loop iteration so that this
        # operator's own execute() has finished (and its class has been removed
        # from the call stack) before we unregister and reload everything.
        def _do_reload():
            root_mod = sys.modules.get(root_pkg)
            if root_mod and hasattr(root_mod, "unregister"):
                try:
                    root_mod.unregister()
                except Exception as exc:
                    print(f"[Simple Export] unregister error: {exc}")

            for name in mod_names:
                mod = sys.modules.get(name)
                if mod is not None:
                    try:
                        importlib.reload(mod)
                    except Exception as exc:
                        print(f"[Simple Export] reload error for '{name}': {exc}")

            # Re-fetch root after in-place reload to pick up any top-level changes.
            root_mod = sys.modules.get(root_pkg)
            if root_mod and hasattr(root_mod, "register"):
                try:
                    root_mod.register()
                except Exception as exc:
                    print(f"[Simple Export] register error: {exc}")

            print(f"[Simple Export] Reloaded {len(mod_names)} modules from '{root_pkg}'")

        bpy.app.timers.register(_do_reload, first_interval=0.0)
        self.report({'INFO'}, f"Queued reload of {len(mod_names)} modules…")
        return {'FINISHED'}

classes = (
    VIEW3D_OT_simple_export_reload,
)


# Register the scene property
def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
