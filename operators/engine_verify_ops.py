import os
import queue
import threading

import bpy

from .. import __package__ as base_package
from ..engine_bridge import (
    VerificationCancelled,
    available_engine_ids,
    run_verification,
)
from ..engine_bridge.mcp_client import MCPClient, MCPError, MCPTransportError

_ENGINE_LABELS = {
    'UNITY': "Unity",
    'GODOT': "Godot",
    'UNREAL': "Unreal",
}


def _engine_settings_for(prefs, engine_id):
    return getattr(prefs, f"engine_mcp_{engine_id.lower()}", None)


def _engine_enum_items(self, context):
    items = [(engine_id, _ENGINE_LABELS.get(engine_id, engine_id.title()), "")
             for engine_id in available_engine_ids()]
    return items or [('NONE', "No Engine Available", "")]


class SIMPLEEXPORT_OT_test_engine_connection(bpy.types.Operator):
    """Send a quick MCP handshake to confirm the engine's MCP server is reachable"""
    bl_idname = "simple_export.test_engine_connection"
    bl_label = "Test Engine Connection"
    bl_options = {'REGISTER', 'INTERNAL'}

    engine_id: bpy.props.StringProperty()

    def execute(self, context):
        prefs = context.preferences.addons[base_package].preferences
        settings = _engine_settings_for(prefs, self.engine_id)
        if settings is None:
            self.report({'ERROR'}, f"Unknown engine '{self.engine_id}'.")
            return {'CANCELLED'}

        client = MCPClient(f"http://{settings.host}:{settings.port}/mcp", timeout=settings.timeout)
        try:
            client.initialize()
        except MCPTransportError as exc:
            settings.last_status = f"Unreachable: {exc}"
            self.report({'WARNING'}, settings.last_status)
            return {'CANCELLED'}
        except MCPError as exc:
            settings.last_status = f"Error: {exc}"
            self.report({'WARNING'}, settings.last_status)
            return {'CANCELLED'}

        settings.last_status = "OK"
        self.report({'INFO'}, f"Connected to {_ENGINE_LABELS.get(self.engine_id, self.engine_id)}.")
        return {'FINISHED'}


def _worker(engine_id, host, port, timeout, filepath, collection_name, out_queue, cancel_event):
    """Background thread body. Never touches bpy.* - see run_verification's docstring."""
    try:
        result = run_verification(
            engine_id, host, port, timeout, filepath, collection_name,
            progress_callback=lambda text: out_queue.put(('progress', text)),
            cancel_event=cancel_event,
        )
        out_queue.put(('done', result))
    except VerificationCancelled:
        out_queue.put(('error', "Verification cancelled."))
    except MCPTransportError as exc:
        out_queue.put(('error', f"Could not reach {_ENGINE_LABELS.get(engine_id, engine_id)}'s MCP server "
                                 f"at {host}:{port} - is it running with its MCP server enabled? ({exc})"))
    except MCPError as exc:
        out_queue.put(('error', str(exc)))
    except Exception as exc:  # noqa: BLE001 - background thread must never crash Blender
        out_queue.put(('error', str(exc)))


def _apply_result_to_ui(context, result):
    """Main-thread-only: writes the verification result into WindowManager
    state and the shared validation-issue list. Never called from a
    background thread."""
    wm = context.window_manager

    if result.screenshot_bytes:
        image_path = os.path.join(
            bpy.app.tempdir,
            f"simple_export_verify_{result.engine_id}_{result.collection_name}.png",
        )
        with open(image_path, 'wb') as f:
            f.write(result.screenshot_bytes)
        image = bpy.data.images.load(image_path, check_existing=False)
        wm.simple_export_engine_verify_image_name = image.name
    else:
        wm.simple_export_engine_verify_image_name = ""

    # Drop any previous engine-verification issues for this collection before
    # appending the fresh ones, so re-running verification doesn't duplicate
    # rows - pre-export validation issues (a different check_id prefix) are
    # left untouched.
    results = wm.simple_export_validation_results
    keep_indices = [
        i for i, item in enumerate(results)
        if not (item.check_id.startswith('engine_') and item.collection_name == result.collection_name)
    ]
    if len(keep_indices) != len(results):
        kept = [
            (results[i].check_id, results[i].collection_name, results[i].object_name,
             results[i].severity, results[i].message)
            for i in keep_indices
        ]
        results.clear()
        for check_id, collection_name, object_name, severity, message in kept:
            item = results.add()
            item.check_id = check_id
            item.collection_name = collection_name
            item.object_name = object_name
            item.severity = severity
            item.message = message

    for issue in result.issues:
        item = results.add()
        item.check_id = issue.check_id
        item.collection_name = issue.collection_name
        item.object_name = issue.object_name
        item.severity = issue.severity
        item.message = issue.message


class SIMPLEEXPORT_OT_verify_in_engine(bpy.types.Operator):
    """Import the exported file into a running game engine via MCP and verify it"""
    bl_idname = "simple_export.verify_in_engine"
    bl_label = "Verify in Engine"
    bl_options = {'REGISTER'}

    collection_name: bpy.props.StringProperty()
    engine_id: bpy.props.EnumProperty(name="Engine", items=_engine_enum_items)
    filepath: bpy.props.StringProperty()

    _thread = None
    _queue = None
    _timer = None
    _cancel_event = None

    def invoke(self, context, event):
        if self.engine_id not in available_engine_ids():
            self.report({'WARNING'}, f"No adapter available yet for engine '{self.engine_id}'.")
            return {'CANCELLED'}

        prefs = context.preferences.addons[base_package].preferences
        if self.engine_id == 'UNREAL' and not prefs.engine_mcp_unreal_experimental_ack:
            self.report({'WARNING'}, "Enable the Unreal experimental acknowledgement in Add-on Preferences first.")
            return {'CANCELLED'}

        settings = _engine_settings_for(prefs, self.engine_id)
        if settings is None or not settings.enabled:
            self.report({'WARNING'},
                        f"{_ENGINE_LABELS.get(self.engine_id, self.engine_id)} verification is disabled "
                        "in Add-on Preferences.")
            return {'CANCELLED'}

        self._queue = queue.Queue()
        self._cancel_event = threading.Event()
        self._thread = threading.Thread(
            target=_worker,
            args=(self.engine_id, settings.host, settings.port, settings.timeout,
                  self.filepath, self.collection_name, self._queue, self._cancel_event),
            daemon=True,
        )
        self._thread.start()

        wm = context.window_manager
        wm.simple_export_engine_verify_running = True
        if context.workspace:
            context.workspace.status_text_set(text=f"Verifying in {self.engine_id.title()}: connecting...")
        self._timer = wm.event_timer_add(0.15, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def modal(self, context, event):
        if event.type == 'ESC' and self._cancel_event is not None:
            self._cancel_event.set()

        if event.type != 'TIMER':
            return {'PASS_THROUGH'}

        try:
            kind, payload = self._queue.get_nowait()
        except queue.Empty:
            return {'RUNNING_MODAL'}

        if kind == 'progress':
            if context.workspace:
                context.workspace.status_text_set(text=f"Verifying in {self.engine_id.title()}: {payload}")
            return {'RUNNING_MODAL'}

        self._finish(context)

        if kind == 'done':
            _apply_result_to_ui(context, payload)
            error_count = sum(1 for issue in payload.issues if issue.severity == 'ERROR')
            if error_count:
                self.report({'WARNING'}, f"Engine verification found {error_count} error(s).")
            else:
                self.report({'INFO'}, "Engine verification passed.")
            bpy.ops.wm.call_panel(name="SIMPLEEXPORT_PT_EngineVerifyResultsPanel")
            return {'FINISHED'}

        self.report({'ERROR'}, payload)
        return {'CANCELLED'}

    def _finish(self, context):
        context.window_manager.simple_export_engine_verify_running = False
        if context.workspace:
            context.workspace.status_text_set(None)
        if self._timer:
            context.window_manager.event_timer_remove(self._timer)
            self._timer = None

    def cancel(self, context):
        if self._cancel_event is not None:
            self._cancel_event.set()
        self._finish(context)


classes = (
    SIMPLEEXPORT_OT_test_engine_connection,
    SIMPLEEXPORT_OT_verify_in_engine,
)


def register():
    from bpy.utils import register_class
    for cls in classes:
        register_class(cls)


def unregister():
    from bpy.utils import unregister_class
    for cls in reversed(classes):
        if 'bl_rna' in cls.__dict__:
            unregister_class(cls)
