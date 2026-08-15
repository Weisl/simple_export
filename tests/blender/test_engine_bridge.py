"""
Headless Blender tests for engine_bridge/ (Phase 1: generic MCP client core
+ verification orchestration + Unity adapter) and its preferences wiring.

Run with:
    blender --background --python tests/blender/test_engine_bridge.py

Uses tests/blender/_fake_mcp_server.py - a real local HTTP server speaking a
minimal MCP JSON-RPC subset - rather than mocking urllib, so the transport
layer is genuinely exercised. Nothing here requires a live game engine.
"""

import base64
import os
import socket
import sys
import threading
import unittest
from types import SimpleNamespace

import bpy

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
_TESTS_DIR = os.path.dirname(_FILE_DIR)
_ADDON_ROOT = os.path.dirname(_TESTS_DIR)
_EXTENSIONS_ROOT = os.path.dirname(_ADDON_ROOT)

if _EXTENSIONS_ROOT not in sys.path:
    sys.path.insert(0, _EXTENSIONS_ROOT)
if _ADDON_ROOT not in sys.path:
    sys.path.insert(0, _ADDON_ROOT)

from tests.blender._fake_mcp_server import FakeMCPServer, RouteError  # noqa: E402
from simple_export.engine_bridge.mcp_client import (  # noqa: E402
    MCPClient, MCPProtocolError, MCPTransportError,
)
from simple_export.engine_bridge.unity_adapter import (  # noqa: E402
    UnityAdapter, _TOOL_CAPTURE_SCREENSHOT, _TOOL_GET_CONSOLE_MESSAGES, _TOOL_IMPORT_ASSET,
)
from simple_export.engine_bridge.verification import (  # noqa: E402
    VerificationCancelled, guess_engine_for_collection, run_verification,
)
from simple_export.preferences.engine_connections import (  # noqa: E402
    EngineConnectionSettings, register as engine_connections_register,
    unregister as engine_connections_unregister,
)
from simple_export.preferences.preferenecs import SIMPLE_EXPORT_preferences  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_FAKE_PNG = base64.b64encode(b"\x89PNG\r\n\x1a\nfake-image-bytes").decode('ascii')


def _init_route(_params):
    return {"protocolVersion": "2025-06-18", "capabilities": {}, "serverInfo": {"name": "fake", "version": "0.0.0"}}


def _unity_routes(console_text="", import_error=False, screenshot_fails=False):
    def tools_call(params):
        name = params.get('name')
        if name == _TOOL_IMPORT_ASSET:
            if import_error:
                raise RouteError("import failed: unsupported format")
            return {"content": [{"type": "text", "text": "Imported successfully."}]}
        if name == _TOOL_CAPTURE_SCREENSHOT:
            if screenshot_fails:
                return {"content": [], "isError": False}
            return {"content": [{"type": "image", "data": _FAKE_PNG, "mimeType": "image/png"}]}
        if name == _TOOL_GET_CONSOLE_MESSAGES:
            return {"content": [{"type": "text", "text": console_text}]}
        raise RouteError(f"unexpected tool: {name}")

    return {"initialize": _init_route, "tools/call": tools_call}


def _free_closed_port():
    """Bind and immediately close a socket to get a free-but-refused local port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('127.0.0.1', 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


# ---------------------------------------------------------------------------
# MCPClient
# ---------------------------------------------------------------------------

class TestMCPClient(unittest.TestCase):
    def test_initialize_and_call_tool_happy_path(self):
        with FakeMCPServer(_unity_routes()) as server:
            client = MCPClient(server.url, timeout=5.0)
            result = client.initialize()
            self.assertEqual(result.get('protocolVersion'), "2025-06-18")

            content = client.call_tool(_TOOL_IMPORT_ASSET, {"path": "/tmp/foo.fbx"})
            self.assertEqual(content[0]['text'], "Imported successfully.")

    def test_tool_error_raises_protocol_error(self):
        with FakeMCPServer(_unity_routes(import_error=True)) as server:
            client = MCPClient(server.url, timeout=5.0)
            client.initialize()
            with self.assertRaises(MCPProtocolError):
                client.call_tool(_TOOL_IMPORT_ASSET, {"path": "/tmp/foo.fbx"})

    def test_unreachable_server_raises_transport_error(self):
        port = _free_closed_port()
        client = MCPClient(f"http://127.0.0.1:{port}/mcp", timeout=3.0)
        with self.assertRaises(MCPTransportError):
            client.initialize()

    def test_malformed_json_response_raises_protocol_error(self):
        import http.server

        class BadHandler(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                body = b"not json"
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        server = http.server.HTTPServer(('127.0.0.1', 0), BadHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            _, port = server.server_address
            client = MCPClient(f"http://127.0.0.1:{port}/mcp", timeout=5.0)
            with self.assertRaises(MCPProtocolError):
                client.initialize()
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


# ---------------------------------------------------------------------------
# UnityAdapter
# ---------------------------------------------------------------------------

class TestUnityAdapter(unittest.TestCase):
    def test_import_capture_console_mapping(self):
        with FakeMCPServer(_unity_routes(console_text="ERROR: something broke\nINFO: fine")) as server:
            client = MCPClient(server.url, timeout=5.0)
            adapter = UnityAdapter(client)
            adapter.connect()

            import_result = adapter.import_asset("/tmp/foo.fbx")
            self.assertTrue(import_result.success)

            screenshot_result = adapter.capture_screenshot()
            self.assertTrue(screenshot_result.success)
            self.assertTrue(screenshot_result.image_bytes.startswith(b"\x89PNG"))

            messages = adapter.get_console_messages()
            levels = {m.level for m in messages}
            self.assertIn('ERROR', levels)
            self.assertIn('INFO', levels)

    def test_import_failure_surfaces_as_unsuccessful_result(self):
        """A tool-level failure (isError=true) must come back as
        ImportResult(success=False), not raise - otherwise a routine "import
        failed" outcome would crash the verification worker instead of
        producing a clean ValidationIssue."""
        with FakeMCPServer(_unity_routes(import_error=True)) as server:
            client = MCPClient(server.url, timeout=5.0)
            adapter = UnityAdapter(client)
            adapter.connect()
            result = adapter.import_asset("/tmp/foo.fbx")
            self.assertFalse(result.success)
            self.assertIn("import failed", result.message)


# ---------------------------------------------------------------------------
# run_verification
# ---------------------------------------------------------------------------

class TestRunVerification(unittest.TestCase):
    def _host_port(self, server):
        host, port = server._server.server_address
        return host, port

    def test_success_no_issues(self):
        with FakeMCPServer(_unity_routes()) as server:
            host, port = self._host_port(server)
            result = run_verification('UNITY', host, port, 5.0, "/tmp/foo.fbx", "MyCollection")
            self.assertTrue(result.import_ok)
            self.assertEqual(result.issues, [])
            self.assertTrue(result.screenshot_bytes.startswith(b"\x89PNG"))

    def test_import_failure_produces_error_issue(self):
        with FakeMCPServer(_unity_routes(import_error=True)) as server:
            host, port = self._host_port(server)
            result = run_verification('UNITY', host, port, 5.0, "/tmp/foo.fbx", "MyCollection")
            self.assertFalse(result.import_ok)
            self.assertTrue(any(i.check_id == 'engine_import_failed' and i.severity == 'ERROR'
                                 for i in result.issues))

    def test_console_errors_and_warnings_become_issues(self):
        with FakeMCPServer(_unity_routes(console_text="ERROR: boom\nWARNING: careful\nINFO: fyi")) as server:
            host, port = self._host_port(server)
            result = run_verification('UNITY', host, port, 5.0, "/tmp/foo.fbx", "MyCollection")
            engine_console_issues = [i for i in result.issues if i.check_id == 'engine_console_message']
            self.assertEqual(len(engine_console_issues), 2)  # INFO is not surfaced as an issue
            self.assertTrue(any(i.severity == 'ERROR' for i in engine_console_issues))
            self.assertTrue(any(i.severity == 'WARNING' for i in engine_console_issues))

    def test_cancel_event_set_before_call_raises_cancelled(self):
        with FakeMCPServer(_unity_routes()) as server:
            host, port = self._host_port(server)
            cancel_event = threading.Event()
            cancel_event.set()
            with self.assertRaises(VerificationCancelled):
                run_verification('UNITY', host, port, 5.0, "/tmp/foo.fbx", "MyCollection",
                                  cancel_event=cancel_event)

    def test_unknown_engine_raises_value_error(self):
        with self.assertRaises(ValueError):
            run_verification('NONEXISTENT_ENGINE', '127.0.0.1', 1, 1.0, "/tmp/foo.fbx", "MyCollection")


# ---------------------------------------------------------------------------
# guess_engine_for_collection
# ---------------------------------------------------------------------------

class TestGuessEngineForCollection(unittest.TestCase):
    def _collection(self, preset_name):
        return SimpleNamespace(simple_export_export_preset=preset_name)

    def test_unity_prefix(self):
        self.assertEqual(guess_engine_for_collection(self._collection("Unity-fbx")), 'UNITY')

    def test_godot_prefix(self):
        self.assertEqual(guess_engine_for_collection(self._collection("Godot-default")), 'GODOT')

    def test_ue_prefix(self):
        self.assertEqual(guess_engine_for_collection(self._collection("UE-fbx")), 'UNREAL')

    def test_empty_preset_returns_none(self):
        self.assertIsNone(guess_engine_for_collection(self._collection("")))

    def test_unknown_prefix_returns_none(self):
        self.assertIsNone(guess_engine_for_collection(self._collection("Custom-fbx")))

    def test_none_collection_returns_none(self):
        self.assertIsNone(guess_engine_for_collection(None))


# ---------------------------------------------------------------------------
# preferences/engine_connections.py register/unregister
#
# EngineConnectionSettings must be registered *before* SIMPLE_EXPORT_preferences
# (whose class body references it in a PointerProperty), and unregistered
# *after* - the reverse of registration order, matching every other
# register()/unregister() pair in this addon. Getting this backwards, or
# post-hoc-assigning the PointerProperty after SIMPLE_EXPORT_preferences is
# already registered (as an earlier version of this code did), silently
# leaves the attribute as an inert _PropertyDeferred that raises on access -
# hasattr() alone does not catch that, so this test exercises real instance
# access, not just attribute presence.
# ---------------------------------------------------------------------------

class TestEngineConnectionsLifecycle(unittest.TestCase):
    """Exercises the real addon_utils.enable()/disable() path (the same one
    Blender uses when a user actually enables the addon) rather than just
    register_class(), so a real AddonPreferences instance backed by RNA is
    reachable via context.preferences.addons[...] - proving the properties
    are genuinely usable, not just present as class attributes."""

    def test_engine_properties_usable_on_a_real_addon_preferences_instance(self):
        import addon_utils
        addon_name = "simple_export"

        addon_utils.enable(addon_name, default_set=True, persistent=False)
        try:
            prefs = bpy.context.preferences.addons[addon_name].preferences
            # Un-bootstrapped state: bpy.app.timers.register()'s callback has
            # not had a chance to fire yet (the test doesn't drive Blender's
            # timer loop), so every engine still sits at the generic
            # class-level default - proving the properties are genuinely
            # readable/writable, independent of the bootstrap timing.
            self.assertEqual(prefs.engine_mcp_unity.port, 8080)
            self.assertFalse(prefs.engine_mcp_unity.enabled)
            self.assertFalse(prefs.engine_verify_auto_trigger)
            self.assertFalse(prefs.engine_mcp_unreal_experimental_ack)

            prefs.engine_mcp_unity.port = 12345
            self.assertEqual(prefs.engine_mcp_unity.port, 12345)

            # _bootstrap_default_ports() applies the real per-engine defaults
            # once, without overwriting a value the user (or this test) has
            # already changed away from the generic default.
            from simple_export.preferences.engine_connections import _bootstrap_default_ports
            _bootstrap_default_ports()
            self.assertEqual(prefs.engine_mcp_unity.port, 12345)  # untouched - no longer at generic default
            self.assertEqual(prefs.engine_mcp_unreal.port, 8000)  # bootstrapped to its real default
        finally:
            addon_utils.disable(addon_name, default_set=True)

        self.assertNotIn('bl_rna', SIMPLE_EXPORT_preferences.__dict__)
        self.assertNotIn('bl_rna', EngineConnectionSettings.__dict__)
        self.assertNotIn('bl_rna', EngineConnectionSettings.__dict__)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
