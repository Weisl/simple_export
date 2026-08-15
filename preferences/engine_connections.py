import bpy
from bpy.props import BoolProperty, FloatProperty, IntProperty, StringProperty

# Per-engine sane default port. EngineConnectionSettings itself keeps a
# generic class-level default (see below) since one PropertyGroup class is
# shared by all three engines; the real default is applied once per engine in
# register(), matching how preferenecs.py's post_register() bootstraps Scene
# properties from AddonPreferences on first activation.
_DEFAULT_PORTS = {
    "unity": 8090,
    "godot": 8080,  # placeholder - confirm real default when Godot support is added
    "unreal": 8000,
}

ENGINE_PROPERTY_METADATA = {
    "host": {"name": "Host", "description": "MCP server host (usually 127.0.0.1)", "default": "127.0.0.1"},
    "port": {"name": "Port", "description": "MCP server port", "default": 8080},
    "enabled": {"name": "Enabled", "description": "Enable engine verification for this engine", "default": False},
    "timeout": {"name": "Timeout (s)", "description": "Seconds to wait for each MCP call before failing",
                "default": 8.0},
}


class EngineConnectionSettings(bpy.types.PropertyGroup):
    """Connection settings for a single engine's local MCP server.

    Note: registered on its own (see register() below) - it must exist
    *before* SIMPLE_EXPORT_preferences is registered, since preferenecs.py
    references this class in a PointerProperty in SIMPLE_EXPORT_preferences'
    class body. Unlike core ID types (Collection, Scene, WindowManager),
    assigning a PointerProperty onto an already-registered AddonPreferences
    class post-hoc does not work - it leaves the attribute as an inert
    _PropertyDeferred rather than a usable property - so this cannot be
    attached after the fact the way preferences/collection_setup.py attaches
    onto bpy.types.Collection.
    """
    host: StringProperty(
        name=ENGINE_PROPERTY_METADATA["host"]["name"],
        description=ENGINE_PROPERTY_METADATA["host"]["description"],
        default=ENGINE_PROPERTY_METADATA["host"]["default"],
    )
    port: IntProperty(
        name=ENGINE_PROPERTY_METADATA["port"]["name"],
        description=ENGINE_PROPERTY_METADATA["port"]["description"],
        default=ENGINE_PROPERTY_METADATA["port"]["default"],
        min=1, max=65535,
    )
    enabled: BoolProperty(
        name=ENGINE_PROPERTY_METADATA["enabled"]["name"],
        description=ENGINE_PROPERTY_METADATA["enabled"]["description"],
        default=ENGINE_PROPERTY_METADATA["enabled"]["default"],
    )
    timeout: FloatProperty(
        name=ENGINE_PROPERTY_METADATA["timeout"]["name"],
        description=ENGINE_PROPERTY_METADATA["timeout"]["description"],
        default=ENGINE_PROPERTY_METADATA["timeout"]["default"],
        min=1.0, soft_max=60.0,
    )
    last_status: StringProperty(default="Not tested", options={'SKIP_SAVE'})


classes = (EngineConnectionSettings,)


def _bootstrap_default_ports():
    """Applies the real per-engine default port on first activation only -
    i.e. only while the setting is still at EngineConnectionSettings' generic
    class-level default, so a user's saved choice is never overwritten."""
    from .. import __package__ as base_package
    addon = bpy.context.preferences.addons.get(base_package)
    if addon is None:
        return
    prefs = addon.preferences
    generic_default = ENGINE_PROPERTY_METADATA["port"]["default"]
    for engine_key, port in _DEFAULT_PORTS.items():
        settings = getattr(prefs, f"engine_mcp_{engine_key}", None)
        if settings is not None and settings.port == generic_default:
            settings.port = port


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)

    bpy.app.timers.register(_bootstrap_default_ports, first_interval=0.5)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)


def _draw_engine_box(layout, settings, label, engine_key):
    box = layout.box()
    row = box.row(align=True)
    row.prop(settings, 'enabled', text="")
    row.label(text=label)
    col = box.column(align=True)
    col.enabled = settings.enabled
    col.prop(settings, 'host')
    col.prop(settings, 'port')
    col.prop(settings, 'timeout')
    row = col.row(align=True)
    row.operator("simple_export.test_engine_connection", text="Test Connection").engine_id = engine_key
    row.label(text=settings.last_status or "Not tested")


def draw_engine_verify_panel(context, layout, prefs):
    """Called from preferenecs.py's draw() for the 'ENGINE' tab."""
    box = layout.box()
    box.label(text="Connect to a running game engine's MCP server to verify exports after they land in-engine.",
              icon='INFO')

    _draw_engine_box(layout, prefs.engine_mcp_unity, "Unity", 'UNITY')
    _draw_engine_box(layout, prefs.engine_mcp_godot, "Godot", 'GODOT')

    box = layout.box()
    box.label(text="Unreal's MCP plugin is experimental (UE 5.8+). Behavior may change.", icon='ERROR')
    box.prop(prefs, 'engine_mcp_unreal_experimental_ack')
    settings = prefs.engine_mcp_unreal
    row = box.row(align=True)
    row.enabled = prefs.engine_mcp_unreal_experimental_ack
    row.prop(settings, 'enabled', text="")
    row.label(text="Unreal")
    col = box.column(align=True)
    col.enabled = prefs.engine_mcp_unreal_experimental_ack and settings.enabled
    col.prop(settings, 'host')
    col.prop(settings, 'port')
    col.prop(settings, 'timeout')
    row = col.row(align=True)
    row.operator("simple_export.test_engine_connection", text="Test Connection").engine_id = 'UNREAL'
    row.label(text=settings.last_status or "Not tested")

    layout.separator()
    layout.prop(prefs, 'engine_verify_auto_trigger')
